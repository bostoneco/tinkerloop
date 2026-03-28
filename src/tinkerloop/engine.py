from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tinkerloop.adapters.base import AppAdapter, TraceCaptureError
from tinkerloop.models import (
    CheckResult,
    Scenario,
    ScenarioCheck,
    ScenarioResult,
    ScenarioTurn,
    TurnResult,
)

SUPPORTED_CHECK_TYPES = (
    "assistant_contains_all",
    "assistant_contains_any",
    "assistant_not_contains",
    "tool_used",
    "tool_call_count_at_most",
    "tool_call_matches",
)

TOOL_CHECK_TYPES = {
    "tool_used",
    "tool_call_count_at_most",
    "tool_call_matches",
}


class ScenarioDefinitionError(ValueError):
    pass


def load_scenarios(path: str | Path) -> list[Scenario]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario path not found: {path}")
    files = [path] if path.is_file() else sorted(path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No scenario files found in {path}")
    scenarios: list[Scenario] = []
    seen_scenario_ids: set[str] = set()
    for file_path in files:
        with open(file_path, encoding="utf-8") as f:
            payload = json.load(f)
        scenario = _parse_scenario_payload(payload, source=file_path)
        scenario_id = scenario.scenario_id
        if scenario_id in seen_scenario_ids:
            raise ValueError(f"Duplicate scenario_id found: {scenario_id}")
        seen_scenario_ids.add(scenario_id)
        scenarios.append(scenario)
    return scenarios


def select_scenarios(
    scenarios: list[Scenario],
    *,
    allow_destructive: bool = False,
    scenario_filter: set[str] | None = None,
    tag_filter: set[str] | None = None,
) -> list[Scenario]:
    selected: list[Scenario] = []
    for scenario in scenarios:
        if scenario_filter and scenario.scenario_id not in scenario_filter:
            continue
        if tag_filter and not tag_filter.intersection(set(scenario.tags)):
            continue
        if scenario.destructive and not allow_destructive:
            continue
        selected.append(scenario)
    return selected


def run_scenarios(
    scenarios: list[Scenario],
    *,
    adapter: AppAdapter,
    user_id: str,
    allow_destructive: bool = False,
    scenario_filter: set[str] | None = None,
    tag_filter: set[str] | None = None,
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for scenario in select_scenarios(
        scenarios,
        allow_destructive=allow_destructive,
        scenario_filter=scenario_filter,
        tag_filter=tag_filter,
    ):
        results.append(run_scenario(scenario, adapter=adapter, user_id=user_id))
    return results


def run_scenario(scenario: Scenario, *, adapter: AppAdapter, user_id: str) -> ScenarioResult:
    _validate_scenario(scenario)
    started = time.time()
    turns: list[TurnResult] = []
    all_passed = True

    for index, turn in enumerate(scenario.turns, start=1):
        turn_started = time.time()
        correlation_id = f"eval-{scenario.scenario_id}-{index}-{uuid.uuid4().hex[:8]}"
        tracer = None
        tool_traces: list[Any] = []
        assistant = ""
        target_called = False
        send_completed = False
        try:
            tracer = adapter.trace_recorder()
        except Exception as exc:
            checks = _trace_capture_failure_checks(
                turn,
                assistant="",
                detail=f"Could not initialize trace capture: {type(exc).__name__}: {exc}",
                include_assistant_checks=False,
            )
        else:
            try:
                with tracer:
                    target_called = True
                    assistant = adapter.send_user_turn(
                        user_id=user_id,
                        user_text=turn.user,
                        correlation_id=correlation_id,
                    )
                    send_completed = True
            except TraceCaptureError as exc:
                tool_traces = _safe_tool_traces(tracer)
                checks = _trace_capture_failure_checks(
                    turn,
                    assistant=assistant,
                    detail=str(exc),
                    include_assistant_checks=send_completed,
                )
            except Exception as exc:
                tool_traces = _safe_tool_traces(tracer)
                trace_error = _trace_capture_detail(tracer)
                if not target_called:
                    checks = _trace_capture_failure_checks(
                        turn,
                        assistant="",
                        detail=f"Could not initialize trace capture: {type(exc).__name__}: {exc}",
                        include_assistant_checks=False,
                    )
                elif send_completed:
                    checks = _trace_capture_failure_checks(
                        turn,
                        assistant=assistant,
                        detail=f"Could not finalize trace capture: {type(exc).__name__}: {exc}",
                        include_assistant_checks=True,
                    )
                else:
                    assistant = ""
                    checks = _adapter_runtime_failure_checks(exc, trace_error=trace_error)
            else:
                tool_traces = _safe_tool_traces(tracer)
                checks = evaluate_checks(assistant=assistant, tool_traces=tool_traces, checks=turn.checks)
        passed = all(item.passed for item in checks)
        all_passed = all_passed and passed
        turns.append(
            TurnResult(
                user=turn.user,
                assistant=assistant,
                tool_traces=tool_traces,
                checks=checks,
                passed=passed,
                duration_ms=int((time.time() - turn_started) * 1000),
            )
        )

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        destructive=scenario.destructive,
        user_id=user_id,
        started_at=int(started),
        duration_ms=int((time.time() - started) * 1000),
        passed=all_passed,
        turns=turns,
    )


def evaluate_checks(
    *, assistant: str, tool_traces: list[Any], checks: list[ScenarioCheck]
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in checks:
        if check.type == "assistant_contains_all":
            missing = [item for item in check.values if item not in assistant]
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=not missing,
                    detail="all substrings present"
                    if not missing
                    else f"missing substrings: {missing}",
                )
            )
            continue
        if check.type == "assistant_contains_any":
            present = [item for item in check.values if item in assistant]
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=bool(present),
                    detail=f"present: {present}" if present else f"none present: {check.values}",
                )
            )
            continue
        if check.type == "assistant_not_contains":
            present = [item for item in check.values if item in assistant]
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=not present,
                    detail="forbidden substrings absent"
                    if not present
                    else f"forbidden substrings present: {present}",
                )
            )
            continue
        if check.type == "tool_used":
            used = {trace.tool_name for trace in tool_traces}
            missing = [item for item in check.values if item not in used]
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=not missing,
                    detail="required tools used" if not missing else f"missing tools: {missing}",
                )
            )
            continue
        if check.type == "tool_call_count_at_most":
            if check.tool:
                count = sum(1 for trace in tool_traces if trace.tool_name == check.tool)
            else:
                count = len(tool_traces)
            max_allowed = int(check.max if check.max is not None else check.value or 0)
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=count <= max_allowed,
                    detail=f"count={count}, max={max_allowed}",
                )
            )
            continue
        if check.type == "tool_call_matches":
            match = any(
                trace.tool_name == str(check.tool)
                and dict_contains(trace.arguments, check.arguments)
                for trace in tool_traces
            )
            results.append(
                CheckResult(
                    check_type=check.type,
                    passed=match,
                    detail=(
                        f"matched tool={check.tool} args={check.arguments}"
                        if match
                        else f"no tool call matched tool={check.tool} args={check.arguments}"
                    ),
                )
            )
            continue
        raise ScenarioDefinitionError(f"Unsupported check type: {check.type}")
    return results


def _parse_scenario_payload(payload: Any, *, source: Path) -> Scenario:
    if not isinstance(payload, dict):
        raise ScenarioDefinitionError(f"Scenario file `{source}` must contain a JSON object.")

    scenario_id = str(payload.get("scenario_id") or "").strip()
    if not scenario_id:
        raise ScenarioDefinitionError(f"Scenario file `{source}` must define a non-empty `scenario_id`.")

    raw_turns = payload.get("turns")
    if not isinstance(raw_turns, list) or not raw_turns:
        raise ScenarioDefinitionError(f"Scenario `{scenario_id}` must define at least one turn.")

    raw_tags = payload.get("tags", [])
    if raw_tags is None:
        raw_tags = []
    if not isinstance(raw_tags, list):
        raise ScenarioDefinitionError(f"Scenario `{scenario_id}` must define `tags` as a list.")

    scenario = Scenario(
        scenario_id=scenario_id,
        description=str(payload.get("description") or scenario_id),
        turns=[
            _parse_turn_payload(turn_payload, scenario_id=scenario_id, turn_index=turn_index)
            for turn_index, turn_payload in enumerate(raw_turns, start=1)
        ],
        destructive=bool(payload.get("destructive", False)),
        tags=[str(tag).strip() for tag in raw_tags if str(tag).strip()],
    )
    _validate_scenario(scenario)
    return scenario


def _parse_turn_payload(payload: Any, *, scenario_id: str, turn_index: int) -> ScenarioTurn:
    if not isinstance(payload, dict):
        raise ScenarioDefinitionError(f"Scenario `{scenario_id}` turn {turn_index} must be an object.")

    user = str(payload.get("user") or "").strip()
    if not user:
        raise ScenarioDefinitionError(
            f"Scenario `{scenario_id}` turn {turn_index} must define a non-empty `user` prompt."
        )

    raw_checks = payload.get("checks", [])
    if raw_checks is None:
        raw_checks = []
    if not isinstance(raw_checks, list):
        raise ScenarioDefinitionError(f"Scenario `{scenario_id}` turn {turn_index} must define `checks` as a list.")

    checks: list[ScenarioCheck] = []
    for check_index, check_payload in enumerate(raw_checks, start=1):
        if not isinstance(check_payload, dict):
            raise ScenarioDefinitionError(
                f"Scenario `{scenario_id}` turn {turn_index} check {check_index} must be an object."
            )
        try:
            check = ScenarioCheck(**check_payload)
        except TypeError as exc:
            raise ScenarioDefinitionError(
                f"Scenario `{scenario_id}` turn {turn_index} check {check_index} is invalid: {exc}"
            ) from exc
        _validate_check(check, scenario_id=scenario_id, turn_index=turn_index, check_index=check_index)
        checks.append(check)

    return ScenarioTurn(user=user, checks=checks)


def _validate_scenario(scenario: Scenario) -> None:
    scenario_id = str(scenario.scenario_id).strip()
    if not scenario_id:
        raise ScenarioDefinitionError("Scenario must define a non-empty `scenario_id`.")
    if not scenario.turns:
        raise ScenarioDefinitionError(f"Scenario `{scenario_id}` must define at least one turn.")

    for turn_index, turn in enumerate(scenario.turns, start=1):
        if not str(turn.user).strip():
            raise ScenarioDefinitionError(
                f"Scenario `{scenario_id}` turn {turn_index} must define a non-empty `user` prompt."
            )
        for check_index, check in enumerate(turn.checks, start=1):
            _validate_check(check, scenario_id=scenario_id, turn_index=turn_index, check_index=check_index)


def _validate_check(check: ScenarioCheck, *, scenario_id: str, turn_index: int, check_index: int) -> None:
    if check.type not in SUPPORTED_CHECK_TYPES:
        raise ScenarioDefinitionError(
            f"Scenario `{scenario_id}` turn {turn_index} check {check_index} uses unsupported "
            f"check type `{check.type}`."
        )


def _safe_tool_traces(tracer: Any) -> list[Any]:
    calls = getattr(tracer, "calls", [])
    return list(calls) if isinstance(calls, list) else []


def _trace_capture_detail(tracer: Any) -> str | None:
    detail = getattr(tracer, "capture_error", None)
    if isinstance(detail, str) and detail.strip():
        return detail
    return None


def _adapter_runtime_failure_checks(
    exc: Exception,
    *,
    trace_error: str | None = None,
) -> list[CheckResult]:
    checks = [
        CheckResult(
            check_type="adapter_runtime",
            passed=False,
            detail=f"{type(exc).__name__}: {exc}",
        )
    ]
    if trace_error:
        checks.append(
            CheckResult(
                check_type="trace_capture",
                passed=False,
                detail=trace_error,
            )
        )
    return checks


def _trace_capture_failure_checks(
    turn: ScenarioTurn,
    *,
    assistant: str,
    detail: str,
    include_assistant_checks: bool,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if include_assistant_checks:
        assistant_checks = [check for check in turn.checks if check.type not in TOOL_CHECK_TYPES]
        checks.extend(evaluate_checks(assistant=assistant, tool_traces=[], checks=assistant_checks))
    checks.append(
        CheckResult(
            check_type="trace_capture",
            passed=False,
            detail=detail,
        )
    )
    return checks


def dict_contains(haystack: dict[str, Any], needle: dict[str, Any]) -> bool:
    for key, value in needle.items():
        if key not in haystack:
            return False
        actual = haystack[key]
        if isinstance(value, dict):
            if not isinstance(actual, dict) or not dict_contains(actual, value):
                return False
        elif actual != value:
            return False
    return True


def write_report(
    results: list[ScenarioResult],
    *,
    output_dir: str | Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"tinkerloop-{int(time.time())}.json"
    report_file = output_path / filename
    payload = build_report_payload(results, metadata=metadata)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    latest_file = output_path / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    failure_payload = build_failure_artifact(results, metadata=metadata)
    latest_failures_file = output_path / "latest-failures.json"
    with open(latest_failures_file, "w", encoding="utf-8") as f:
        json.dump(failure_payload, f, indent=2)

    diagnosis_payload = build_diagnosis_artifact(results, metadata=metadata)
    latest_diagnosis_file = output_path / "latest-diagnosis.json"
    with open(latest_diagnosis_file, "w", encoding="utf-8") as f:
        json.dump(diagnosis_payload, f, indent=2)
    return report_file


def summarize_results(results: list[ScenarioResult]) -> str:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = total - passed
    lines = [f"Scenarios: {total}, passed: {passed}, failed: {failed}"]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- [{status}] {result.scenario_id}: {result.description}")
        for index, turn in enumerate(result.turns, start=1):
            if turn.passed:
                continue
            failing = [check.detail for check in turn.checks if not check.passed]
            lines.append(f"  turn {index}: {', '.join(failing)}")
    return "\n".join(lines)


def build_report_payload(
    results: list[ScenarioResult],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = int(time.time())
    failures = _collect_failures(results)
    failed_scenario_ids = [item["scenario_id"] for item in failures]
    failed_turns = sum(1 for result in results for turn in result.turns if not turn.passed)
    metadata = metadata or {}
    return {
        "schema_version": "tinkerloop.report.v1",
        "generated_at": generated_at,
        "metadata": metadata,
        "summary": {
            "scenario_total": len(results),
            "scenario_passed": sum(1 for result in results if result.passed),
            "scenario_failed": sum(1 for result in results if not result.passed),
            "failed_turn_total": failed_turns,
            "failed_scenario_ids": failed_scenario_ids,
            **_report_context(metadata),
        },
        "failures": failures,
        "results": [asdict(result) for result in results],
    }


def build_failure_artifact(
    results: list[ScenarioResult],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures = _collect_failures(results)
    metadata = metadata or {}
    return {
        "schema_version": "tinkerloop.failures.v1",
        "generated_at": int(time.time()),
        "metadata": metadata,
        "summary": {
            "failed_scenario_count": len(failures),
            "failed_scenario_ids": [item["scenario_id"] for item in failures],
            **_report_context(metadata),
        },
        "failures": failures,
    }


def load_failed_scenario_ids(path: str | Path) -> list[str]:
    target = Path(path)
    if target.is_dir():
        for candidate_name in ("latest-failures.json", "latest.json"):
            candidate = target / candidate_name
            if candidate.is_file():
                return load_failed_scenario_ids(candidate)
        reports = sorted(target.glob("tinkerloop-*.json"), reverse=True)
        if reports:
            return load_failed_scenario_ids(reports[0])
        raise FileNotFoundError(f"No Tinkerloop report files found in {target}")

    payload = json.loads(target.read_text(encoding="utf-8"))
    summary = payload.get("summary") or {}
    failed_ids = summary.get("failed_scenario_ids") or []
    if isinstance(failed_ids, list):
        return [str(item) for item in failed_ids if str(item).strip()]

    failures = payload.get("failures") or []
    return [
        str(item.get("scenario_id"))
        for item in failures
        if isinstance(item, dict) and str(item.get("scenario_id") or "").strip()
    ]


def build_diagnosis_artifact(
    results: list[ScenarioResult],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures = _collect_failures(results)
    metadata = metadata or {}
    diagnosis_items = []
    for failure in failures:
        primary_symptoms: list[str] = []
        turns = []
        for turn in failure["failed_turns"]:
            failing_checks = turn["failing_checks"]
            for check in failing_checks:
                detail = str(check.get("detail") or "")
                if detail and detail not in primary_symptoms:
                    primary_symptoms.append(detail)
            turns.append(
                {
                    "turn_index": turn["turn_index"],
                    "user": turn["user"],
                    "assistant_excerpt": _excerpt(str(turn["assistant"])),
                    "failing_checks": failing_checks,
                    "tool_trace_count": turn["tool_trace_count"],
                }
            )
        diagnosis_items.append(
            {
                "scenario_id": failure["scenario_id"],
                "description": failure["description"],
                "primary_symptoms": primary_symptoms[:5],
                "turns": turns,
            }
        )

    failed_ids = [item["scenario_id"] for item in diagnosis_items]
    return {
        "schema_version": "tinkerloop.diagnosis.v1",
        "generated_at": int(time.time()),
        "metadata": metadata,
        "summary": {
            "failed_scenario_count": len(diagnosis_items),
            "failed_scenario_ids": failed_ids,
            **_report_context(metadata),
        },
        "diagnosis_items": diagnosis_items,
        "rerun": {
            "scenario_ids": failed_ids,
            "hint": "--failed-from <report-dir-or-report-file>",
        },
    }


def _collect_failures(results: list[ScenarioResult]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for result in results:
        if result.passed:
            continue
        turn_failures = []
        for index, turn in enumerate(result.turns, start=1):
            failing_checks = [asdict(check) for check in turn.checks if not check.passed]
            if not failing_checks:
                continue
            turn_failures.append(
                {
                    "turn_index": index,
                    "user": turn.user,
                    "assistant": turn.assistant,
                    "failing_checks": failing_checks,
                    "tool_trace_count": len(turn.tool_traces),
                }
            )
        failures.append(
            {
                "scenario_id": result.scenario_id,
                "description": result.description,
                "failed_turns": turn_failures,
            }
        )
    return failures


def _excerpt(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _report_context(metadata: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    preflight = metadata.get("preflight")
    if isinstance(preflight, dict):
        status = str(preflight.get("status") or "").strip()
        if status:
            context["preflight_status"] = status

    runtime = metadata.get("selected_runtime")
    if not isinstance(runtime, dict):
        runtime = metadata.get("resolved_runtime")
    if isinstance(runtime, dict):
        provider = str(runtime.get("provider") or "").strip()
        model = str(runtime.get("model") or "").strip()
        if provider or model:
            context["selected_runtime"] = {
                "provider": provider,
                "model": model,
            }

    return context
