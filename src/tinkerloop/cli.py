from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

from tinkerloop.__about__ import __version__
from tinkerloop.adapters.base import AppAdapter
from tinkerloop.engine import (
    load_failed_scenario_ids,
    load_scenarios,
    run_scenarios,
    select_scenarios,
    summarize_results,
    write_report,
)
from tinkerloop.models import RuntimeSpec

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_adapter(factory_path: str):
    module_name, _, attr_name = factory_path.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid adapter factory path: {factory_path}")
    module = _load_adapter_module(module_name)
    factory = getattr(module, attr_name)
    adapter = factory()
    return adapter


def _load_adapter_module(module_name: str):
    file_path = Path(module_name).expanduser()
    looks_like_file = file_path.suffix == ".py" or any(
        marker in module_name for marker in ("/", "\\")
    )
    if looks_like_file:
        resolved = file_path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Adapter module file not found: {resolved}")
        spec = importlib.util.spec_from_file_location(
            f"tinkerloop_target_adapter_{resolved.stem}_{abs(hash(str(resolved)))}",
            resolved,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load adapter module from file: {resolved}")
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(spec.name, module)
        spec.loader.exec_module(module)
        return module
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    return importlib.import_module(module_name)


def resolve_runtime_selection(
    *,
    adapter: AppAdapter,
    user_id: str,
    inner_provider: str = "",
    inner_model: str = "",
    interactive: bool | None = None,
    input_func=input,
    output_stream=None,
) -> tuple[RuntimeSpec, dict[str, object]]:
    output_stream = output_stream or sys.stdout
    resolved = adapter.runtime_spec(user_id=user_id)
    metadata: dict[str, object] = {
        "resolved_runtime": asdict(resolved) if resolved else None,
    }

    if inner_provider or inner_model:
        selected = _build_override_runtime(
            resolved=resolved,
            candidates=adapter.runtime_candidates(user_id=user_id),
            inner_provider=inner_provider,
            inner_model=inner_model,
        )
        adapter.select_runtime(selected)
        metadata["runtime_selection_mode"] = "override"
        metadata["selected_runtime"] = asdict(selected)
        return selected, metadata

    if resolved:
        adapter.select_runtime(resolved)
        metadata["runtime_selection_mode"] = "resolved"
        metadata["selected_runtime"] = asdict(resolved)
        return resolved, metadata

    candidates = adapter.runtime_candidates(user_id=user_id)
    metadata["runtime_candidates"] = [asdict(candidate) for candidate in candidates]
    if not candidates:
        raise RuntimeError(
            "The adapter could not identify a compatible inner model from the target repo. "
            "Provide --inner-provider and --inner-model explicitly."
        )

    if interactive is None:
        interactive = bool(sys.stdin.isatty() and sys.stdout.isatty())
    if not interactive:
        raise RuntimeError(_format_runtime_candidates_error(candidates))

    selected = _prompt_for_runtime_candidate(
        candidates=candidates,
        input_func=input_func,
        output_stream=output_stream,
    )
    adapter.select_runtime(selected)
    metadata["runtime_selection_mode"] = "interactive_candidate"
    metadata["selected_runtime"] = asdict(selected)
    return selected, metadata


def _build_override_runtime(
    *,
    resolved: RuntimeSpec | None,
    candidates: list[RuntimeSpec],
    inner_provider: str,
    inner_model: str,
) -> RuntimeSpec:
    normalized_provider = inner_provider.strip().lower()
    model = inner_model.strip()

    if normalized_provider and model:
        return RuntimeSpec(
            provider=normalized_provider,
            model=model,
            source="cli_override",
            confidence="explicit",
            reason="Explicit runtime override from CLI arguments.",
        )

    pool = [resolved] if resolved else []
    pool.extend(candidates)
    if normalized_provider and not model:
        for item in pool:
            if item and item.provider == normalized_provider:
                return RuntimeSpec(
                    provider=item.provider,
                    model=item.model,
                    source="cli_override",
                    confidence="explicit",
                    reason="CLI provider override combined with the best matching target-repo model.",
                )
        raise RuntimeError(
            f"No compatible model candidate was found for provider `{normalized_provider}`."
        )

    if model and not normalized_provider:
        for item in pool:
            if item and item.model == model:
                return RuntimeSpec(
                    provider=item.provider,
                    model=item.model,
                    source="cli_override",
                    confidence="explicit",
                    reason="CLI model override combined with the best matching target-repo provider.",
                )
        raise RuntimeError(f"No compatible provider candidate was found for model `{model}`.")

    raise RuntimeError("Runtime override requires at least --inner-provider or --inner-model.")


def _format_runtime_candidates_error(candidates: list[RuntimeSpec]) -> str:
    lines = [
        "The adapter could not resolve one inner model automatically. Choose one explicitly with --inner-provider/--inner-model.",
        "Repo-derived candidates:",
    ]
    for index, candidate in enumerate(candidates, start=1):
        lines.append(
            f"{index}. {candidate.provider} / {candidate.model} [{candidate.confidence}] - {candidate.reason}"
        )
    return "\n".join(lines)


def _prompt_for_runtime_candidate(
    *,
    candidates: list[RuntimeSpec],
    input_func=input,
    output_stream=None,
) -> RuntimeSpec:
    output_stream = output_stream or sys.stdout
    print("Select the inner runtime for the target app:", file=output_stream)
    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index}. {candidate.provider} / {candidate.model} [{candidate.confidence}] - {candidate.reason}",
            file=output_stream,
        )

    while True:
        raw = input_func("Choice: ").strip()
        if raw.lower() in {"q", "quit", "exit"}:
            raise RuntimeError("Runtime selection cancelled by user.")
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(candidates):
                return candidates[choice - 1]
        print("Enter a valid number from the list, or `q` to cancel.", file=output_stream)


def _write_error_report(
    *,
    report_dir: str,
    metadata: dict[str, object],
    message: str,
    metadata_key: str | None = None,
) -> int:
    if metadata_key:
        metadata[metadata_key] = message
    report_file = write_report([], output_dir=report_dir, metadata=metadata)
    print(message, file=sys.stderr)
    print(f"Report: {report_file}", file=sys.stderr)
    return 2


def _format_empty_selection_error(
    *,
    scenario_filter: set[str],
    tag_filter: set[str],
    allow_destructive: bool,
) -> str:
    details: list[str] = []
    if scenario_filter:
        details.append(f"scenario ids={sorted(scenario_filter)}")
    if tag_filter:
        details.append(f"tags={sorted(tag_filter)}")
    if not allow_destructive:
        details.append("destructive scenarios excluded")
    if not details:
        return "No scenarios were selected to run."
    return f"No scenarios matched the current selection ({', '.join(details)})."


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--adapter",
        required=True,
        help="Adapter factory import path or file path (<module-or-file>:<factory>)",
    )
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--inner-provider", default="", help="Override inner provider")
    parser.add_argument("--inner-model", default="", help="Override inner model")
    parser.add_argument(
        "--failed-from",
        default="",
        help="Rerun only failed scenarios from a prior report file or report directory",
    )
    parser.add_argument(
        "--scenarios",
        required=True,
        help="Scenario file or directory",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Specific scenario id to run (repeatable)",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Run only scenarios containing one of these tags (repeatable)",
    )
    parser.add_argument(
        "--allow-destructive",
        action="store_true",
        help="Allow scenarios marked destructive",
    )
    parser.add_argument(
        "--report-dir",
        default="artifacts/reports",
        help="Where to write JSON reports",
    )


def _build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tinkerloop",
        description="Tinkerloop CLI",
        epilog="Use `tinkerloop run ...` to execute scenarios.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    run_parser = subparsers.add_parser(
        "run",
        help="Run scenarios against a target adapter",
        description="Run Tinkerloop scenarios",
    )
    _add_run_arguments(run_parser)
    return parser


def _parse_args(argv: list[str]) -> argparse.Namespace:
    root_parser = _build_root_parser()
    if not argv:
        root_parser.print_help()
        raise SystemExit(0)
    if argv[0] in {"-h", "--help", "--version"}:
        root_parser.parse_args(argv)
        raise AssertionError("parse_args should exit for top-level help/version")
    if argv[0] == "run":
        return root_parser.parse_args(argv)
    if argv[0].startswith("-"):
        root_parser.error("Missing command `run`. Use `tinkerloop run ...`.")
    root_parser.error(f"Unknown command `{argv[0]}`. Use `tinkerloop run ...`.")
    raise AssertionError("root_parser.error should exit")


def _run_command(args: argparse.Namespace) -> int:

    adapter = load_adapter(args.adapter)
    preflight = adapter.preflight(user_id=str(args.user_id))
    metadata = {
        "adapter": adapter.run_metadata(),
        "preflight": asdict(preflight),
    }
    if not preflight.ready:
        return _write_error_report(
            report_dir=args.report_dir,
            metadata=metadata,
            message=preflight.summary,
        )

    try:
        _, runtime_metadata = resolve_runtime_selection(
            adapter=adapter,
            user_id=str(args.user_id),
            inner_provider=str(args.inner_provider),
            inner_model=str(args.inner_model),
        )
    except RuntimeError as exc:
        return _write_error_report(
            report_dir=args.report_dir,
            metadata=metadata,
            message=str(exc),
            metadata_key="runtime_error",
        )

    metadata.update(runtime_metadata)
    try:
        scenarios = load_scenarios(args.scenarios)
        scenario_filter = set(args.scenario) if args.scenario else set()
        tag_filter = set(args.tag) if args.tag else set()
        if args.failed_from:
            failed_ids = load_failed_scenario_ids(args.failed_from)
            scenario_filter.update(failed_ids)
            metadata["rerun_failed_from"] = str(args.failed_from)
            metadata["rerun_failed_scenario_ids"] = sorted(failed_ids)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _write_error_report(
            report_dir=args.report_dir,
            metadata=metadata,
            message=str(exc),
            metadata_key="scenario_error",
        )
    if tag_filter:
        metadata["tag_filter"] = sorted(tag_filter)
    metadata["loaded_scenario_count"] = len(scenarios)
    metadata["scenario_filter"] = sorted(scenario_filter)
    if not scenarios:
        return _write_error_report(
            report_dir=args.report_dir,
            metadata=metadata,
            message="No scenarios were selected to run.",
            metadata_key="scenario_error",
        )
    selected_scenarios = select_scenarios(
        scenarios,
        allow_destructive=bool(args.allow_destructive),
        scenario_filter=scenario_filter or None,
        tag_filter=tag_filter or None,
    )
    metadata["selected_scenario_count"] = len(selected_scenarios)
    if not selected_scenarios:
        return _write_error_report(
            report_dir=args.report_dir,
            metadata=metadata,
            message=_format_empty_selection_error(
                scenario_filter=scenario_filter,
                tag_filter=tag_filter,
                allow_destructive=bool(args.allow_destructive),
            ),
            metadata_key="scenario_error",
        )
    results = run_scenarios(
        scenarios,
        adapter=adapter,
        user_id=str(args.user_id),
        allow_destructive=bool(args.allow_destructive),
        scenario_filter=scenario_filter or None,
        tag_filter=tag_filter or None,
    )
    report_file = write_report(results, output_dir=args.report_dir, metadata=metadata)
    print(summarize_results(results))
    print(f"Report: {report_file}")
    return 0 if all(result.passed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(list(sys.argv[1:] if argv is None else argv))
    return _run_command(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
