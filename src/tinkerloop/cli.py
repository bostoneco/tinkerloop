from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import asdict
from pathlib import Path

from tinkerloop.adapters.base import AppAdapter
from tinkerloop.engine import (
    load_failed_scenario_ids,
    load_scenarios,
    run_scenarios,
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
    module = importlib.import_module(module_name)
    factory = getattr(module, attr_name)
    adapter = factory()
    return adapter


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tinkerloop scenarios")
    parser.add_argument("--adapter", required=True, help="Adapter factory import path")
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
        default="examples/moppa/scenarios",
        help="Scenario file or directory",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Specific scenario id to run (repeatable)",
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
    args = parser.parse_args()

    adapter = load_adapter(args.adapter)
    preflight = adapter.preflight(user_id=str(args.user_id))
    metadata = {
        "adapter": adapter.run_metadata(),
        "preflight": asdict(preflight),
    }
    if not preflight.ready:
        report_file = write_report([], output_dir=args.report_dir, metadata=metadata)
        print(preflight.summary, file=sys.stderr)
        print(f"Report: {report_file}", file=sys.stderr)
        return 2

    try:
        _, runtime_metadata = resolve_runtime_selection(
            adapter=adapter,
            user_id=str(args.user_id),
            inner_provider=str(args.inner_provider),
            inner_model=str(args.inner_model),
        )
    except RuntimeError as exc:
        metadata["runtime_error"] = str(exc)
        report_file = write_report([], output_dir=args.report_dir, metadata=metadata)
        print(str(exc), file=sys.stderr)
        print(f"Report: {report_file}", file=sys.stderr)
        return 2

    metadata.update(runtime_metadata)
    scenarios = load_scenarios(args.scenarios)
    scenario_filter = set(args.scenario) if args.scenario else set()
    if args.failed_from:
        failed_ids = load_failed_scenario_ids(args.failed_from)
        scenario_filter.update(failed_ids)
        metadata["rerun_failed_from"] = str(args.failed_from)
        metadata["rerun_failed_scenario_ids"] = sorted(failed_ids)
    results = run_scenarios(
        scenarios,
        adapter=adapter,
        user_id=str(args.user_id),
        allow_destructive=bool(args.allow_destructive),
        scenario_filter=scenario_filter or None,
    )
    report_file = write_report(results, output_dir=args.report_dir, metadata=metadata)
    print(summarize_results(results))
    print(f"Report: {report_file}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
