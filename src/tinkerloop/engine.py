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


def load_scenarios(path: str | Path) -> list[Scenario]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario path not found: {path}")
    files = [path] if path.is_file() else sorted(path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No scenario files found in {path}")
    scenarios: list[Scenario] = []
    for file_path in files:
        with open(file_path, encoding="utf-8") as f:
            payload = json.load(f)
        turns = [
            ScenarioTurn(
                user=str(turn["user"]),
                checks=[ScenarioCheck(**check) for check in turn.get("checks", [])],
            )
            for turn in payload.get("turns", [])
        ]
        scenarios.append(
            Scenario(
                scenario_id=str(payload["scenario_id"]),
                description=str(payload.get("description") or payload["scenario_id"]),
                turns=turns,
                destructive=bool(payload.get("destructive", False)),
                tags=list(payload.get("tags", [])),
            )
        )
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
    started = time.time()
    turns: list[TurnResult] = []
    all_passed = True

    for index, turn in enumerate(scenario.turns, start=1):
        turn_started = time.time()
        correlation_id = f"eval-{scenario.scenario_id}-{index}-{uuid.uuid4().hex[:8]}"
        tracer = None
        assistant = ""
        try:
            tracer = adapter.trace_recorder()
            with tracer:
                assistant = adapter.send_user_turn(
                    user_id=user_id,
                    user_text=turn.user,
                    correlation_id=correlation_id,
                )
            checks = evaluate_checks(assistant=assistant, tool_traces=tracer.calls, checks=turn.checks)
        except TraceCaptureError as exc:
            assistant_checks = [
                check for check in turn.checks if check.type not in TOOL_CHECK_TYPES
            ]
            checks = evaluate_checks(assistant=assistant, tool_traces=[], checks=assistant_checks)
            checks.append(
                CheckResult(
                    check_type="trace_capture",
                    passed=False,
                    detail=str(exc),
                )
            )
        except Exception as exc:
            assistant = ""
            checks = [
                CheckResult(
                    check_type="adapter_runtime",
                    passed=False,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            ]
        passed = all(item.passed for item in checks)
        all_passed = all_passed and passed
        turns.append(
            TurnResult(
                user=turn.user,
                assistant=assistant,
                tool_traces=tracer.calls,
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
        raise ValueError(f"Unsupported check type: {check.type}")
    return results


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
