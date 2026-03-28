import json

import pytest

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.adapters.command_target import CommandAppAdapter
from tinkerloop.engine import (
    ScenarioDefinitionError,
    SUPPORTED_CHECK_TYPES,
    build_diagnosis_artifact,
    build_failure_artifact,
    build_report_payload,
    dict_contains,
    evaluate_checks,
    load_failed_scenario_ids,
    load_scenarios,
    run_scenario,
    run_scenarios,
    select_scenarios,
    write_report,
)
from tinkerloop.models import Scenario, ScenarioCheck, ScenarioTurn, ToolTrace


class DummyAdapter(AppAdapter):
    def __init__(self) -> None:
        self.recorder = TraceRecorder()

    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        self.recorder.calls = [
            ToolTrace(
                tool_name="cleanup",
                arguments={"dry_run": True, "action": "trash", "query": "from:a"},
                correlation_id=correlation_id,
                duration_ms=5,
                status="ok",
                user_safe_summary="Dry run",
                raw_result={"status": "ok"},
            )
        ]
        return "Preview for the first unit. Undo will be available after execution."

    def trace_recorder(self) -> TraceRecorder:
        return self.recorder


class FailingAdapter(AppAdapter):
    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        raise RuntimeError("boom")


class TraceSetupFailingAdapter(AppAdapter):
    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        return "ok"

    def trace_recorder(self) -> TraceRecorder:
        raise RuntimeError("trace setup boom")


def test_dict_contains_handles_nested_subsets():
    assert dict_contains({"a": 1, "b": {"c": True, "d": 2}}, {"b": {"c": True}})
    assert not dict_contains({"a": 1}, {"b": 2})


def test_evaluate_checks_matches_tool_call_and_reply():
    checks = [
        ScenarioCheck(type="assistant_contains_all", values=["Preview for", "Undo"]),
        ScenarioCheck(type="tool_used", values=["cleanup"]),
        ScenarioCheck(
            type="tool_call_matches",
            tool="cleanup",
            arguments={"dry_run": True, "action": "trash"},
        ),
    ]
    results = evaluate_checks(
        assistant="Preview for the first unit. Undo will be available after execution.",
        tool_traces=[
            ToolTrace(
                tool_name="cleanup",
                arguments={"dry_run": True, "action": "trash", "query": "from:a"},
                correlation_id=None,
                duration_ms=10,
                status="ok",
                user_safe_summary="Dry run",
                raw_result={"status": "ok"},
            )
        ],
        checks=checks,
    )
    assert all(item.passed for item in results)


def test_evaluate_checks_supports_additional_check_types():
    checks = [
        ScenarioCheck(type="assistant_contains_any", values=["missing", "Undo"]),
        ScenarioCheck(type="assistant_not_contains", values=["forbidden"]),
        ScenarioCheck(type="tool_call_count_at_most", tool="cleanup", max=1),
    ]

    results = evaluate_checks(
        assistant="Preview for the first unit. Undo will be available after execution.",
        tool_traces=[
            ToolTrace(
                tool_name="cleanup",
                arguments={"dry_run": True},
                correlation_id=None,
                duration_ms=10,
                status="ok",
                user_safe_summary="Dry run",
                raw_result={"status": "ok"},
            )
        ],
        checks=checks,
    )

    assert all(item.passed for item in results)


def test_supported_check_types_constant_matches_engine_surface():
    assert SUPPORTED_CHECK_TYPES == (
        "assistant_contains_all",
        "assistant_contains_any",
        "assistant_not_contains",
        "tool_used",
        "tool_call_count_at_most",
        "tool_call_matches",
    )


def test_load_scenarios_parses_json_file(tmp_path):
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "description": "demo",
                "turns": [
                    {
                        "user": "Preview the first cleanup unit",
                        "checks": [{"type": "assistant_contains_all", "values": ["Preview for"]}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    scenarios = load_scenarios(scenario_file)

    assert len(scenarios) == 1
    assert scenarios[0].scenario_id == "cleanup_preview_first_unit"
    assert scenarios[0].turns[0].user == "Preview the first cleanup unit"


def test_load_scenarios_fails_for_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scenarios(tmp_path / "missing")


def test_load_scenarios_rejects_duplicate_scenario_ids(tmp_path):
    first = tmp_path / "a.json"
    first.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "turns": [{"user": "Preview"}],
            }
        ),
        encoding="utf-8",
    )
    second = tmp_path / "b.json"
    second.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "turns": [{"user": "Preview again"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        load_scenarios(tmp_path)

    assert "Duplicate scenario_id found" in str(exc.value)


def test_load_scenarios_rejects_empty_turn_lists(tmp_path):
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "turns": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioDefinitionError) as exc:
        load_scenarios(scenario_file)

    assert "must define at least one turn" in str(exc.value)


def test_load_scenarios_rejects_empty_user_prompts(tmp_path):
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "turns": [{"user": "   "}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioDefinitionError) as exc:
        load_scenarios(scenario_file)

    assert "non-empty `user` prompt" in str(exc.value)


def test_load_scenarios_rejects_unsupported_check_types(tmp_path):
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenario_id": "cleanup_preview_first_unit",
                "turns": [
                    {
                        "user": "Preview",
                        "checks": [{"type": "bogus"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioDefinitionError) as exc:
        load_scenarios(scenario_file)

    assert "unsupported check type `bogus`" in str(exc.value)


def test_select_scenarios_applies_filters():
    scenarios = [
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="demo",
            turns=[],
            tags=["cleanup", "preview"],
        ),
        Scenario(
            scenario_id="destructive_cleanup",
            description="demo",
            turns=[],
            destructive=True,
            tags=["cleanup"],
        ),
    ]

    selected = select_scenarios(
        scenarios,
        allow_destructive=False,
        scenario_filter={"cleanup_preview_first_unit", "destructive_cleanup"},
        tag_filter={"preview"},
    )

    assert [scenario.scenario_id for scenario in selected] == ["cleanup_preview_first_unit"]


def test_run_scenario_uses_adapter_and_checks():
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[
            ScenarioTurn(
                user="Preview the first cleanup unit",
                checks=[
                    ScenarioCheck(type="assistant_contains_all", values=["Preview for", "Undo"]),
                    ScenarioCheck(type="tool_used", values=["cleanup"]),
                ],
            )
        ],
    )

    result = run_scenario(scenario, adapter=DummyAdapter(), user_id="u1")

    assert result.passed is True
    assert result.turns[0].tool_traces[0].tool_name == "cleanup"


def test_run_scenario_records_adapter_failure_as_failed_turn():
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[ScenarioTurn(user="Preview the first cleanup unit", checks=[])],
    )

    result = run_scenario(scenario, adapter=FailingAdapter(), user_id="u1")

    assert result.passed is False
    assert result.turns[0].checks[0].check_type == "adapter_runtime"
    assert "boom" in result.turns[0].checks[0].detail


def test_run_scenario_records_trace_setup_failure_as_failed_turn():
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[
            ScenarioTurn(
                user="Preview the first cleanup unit",
                checks=[ScenarioCheck(type="assistant_contains_all", values=["ok"])],
            )
        ],
    )

    result = run_scenario(scenario, adapter=TraceSetupFailingAdapter(), user_id="u1")

    assert result.passed is False
    assert result.turns[0].assistant == ""
    assert result.turns[0].tool_traces == []
    assert len(result.turns[0].checks) == 1
    assert result.turns[0].checks[0].check_type == "trace_capture"
    assert "Could not initialize trace capture" in result.turns[0].checks[0].detail


def test_run_scenario_marks_missing_traces_as_trace_capture_failure(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(
        """
print("Preview ready")
""".strip(),
        encoding="utf-8",
    )
    adapter = CommandAppAdapter(
        command_builder=lambda user_id, user_text, correlation_id: [
            "python",
            str(script),
        ],
        workdir=tmp_path,
    )
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[
            ScenarioTurn(
                user="Preview the first cleanup unit",
                checks=[
                    ScenarioCheck(type="assistant_contains_all", values=["Preview ready"]),
                    ScenarioCheck(type="tool_used", values=["cleanup"]),
                ],
            )
        ],
    )

    result = run_scenario(scenario, adapter=adapter, user_id="u1")

    assert result.passed is False
    assert result.turns[0].assistant == "Preview ready"
    assert result.turns[0].checks[-1].check_type == "trace_capture"
    assert "did not write a trace file" in result.turns[0].checks[-1].detail
    assert all(check.check_type != "tool_used" for check in result.turns[0].checks)


def test_run_scenario_preserves_adapter_failure_when_command_trace_is_missing(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(
        """
import sys
print("boom", file=sys.stderr)
sys.exit(3)
""".strip(),
        encoding="utf-8",
    )
    adapter = CommandAppAdapter(
        command_builder=lambda user_id, user_text, correlation_id: [
            "python",
            str(script),
        ],
        workdir=tmp_path,
    )
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[ScenarioTurn(user="Preview the first cleanup unit", checks=[])],
    )

    result = run_scenario(scenario, adapter=adapter, user_id="u1")

    assert result.passed is False
    assert result.turns[0].assistant == ""
    assert result.turns[0].tool_traces == []
    assert [check.check_type for check in result.turns[0].checks] == [
        "adapter_runtime",
        "trace_capture",
    ]
    assert "boom" in result.turns[0].checks[0].detail
    assert "did not write a trace file" in result.turns[0].checks[1].detail


def test_run_scenario_rejects_invalid_scenarios_before_execution():
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[],
    )

    with pytest.raises(ScenarioDefinitionError) as exc:
        run_scenario(scenario, adapter=DummyAdapter(), user_id="u1")

    assert "must define at least one turn" in str(exc.value)


def test_run_scenario_rejects_unsupported_checks_before_execution():
    scenario = Scenario(
        scenario_id="cleanup_preview_first_unit",
        description="demo",
        turns=[
            ScenarioTurn(
                user="Preview the first cleanup unit",
                checks=[ScenarioCheck(type="bogus")],
            )
        ],
    )

    with pytest.raises(ScenarioDefinitionError) as exc:
        run_scenario(scenario, adapter=DummyAdapter(), user_id="u1")

    assert "unsupported check type `bogus`" in str(exc.value)


def test_build_report_payload_collects_failures():
    failed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="Preview the first cleanup unit",
                    checks=[
                        ScenarioCheck(type="assistant_contains_all", values=["missing substring"])
                    ],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )

    payload = build_report_payload(
        [failed_result],
        metadata={
            "adapter": {"name": "dummy"},
            "preflight": {"status": "ready"},
            "selected_runtime": {"provider": "bedrock", "model": "us.amazon.nova-pro-v1:0"},
        },
    )

    assert payload["schema_version"] == "tinkerloop.report.v1"
    assert payload["summary"]["scenario_failed"] == 1
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_preview_first_unit"]
    assert payload["summary"]["preflight_status"] == "ready"
    assert payload["summary"]["selected_runtime"]["provider"] == "bedrock"
    assert payload["failures"][0]["scenario_id"] == "cleanup_preview_first_unit"
    assert payload["failures"][0]["failed_turns"][0]["failing_checks"][0]["check_type"] == (
        "assistant_contains_all"
    )


def test_write_report_creates_latest_and_latest_failures(tmp_path):
    failed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="Preview the first cleanup unit",
                    checks=[
                        ScenarioCheck(type="assistant_contains_all", values=["missing substring"])
                    ],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )

    report_file = write_report([failed_result], output_dir=tmp_path, metadata={"adapter": {}})

    assert report_file.is_file()
    assert (tmp_path / "latest.json").is_file()
    assert (tmp_path / "latest-failures.json").is_file()
    assert (tmp_path / "latest-diagnosis.json").is_file()

    failure_payload = json.loads((tmp_path / "latest-failures.json").read_text(encoding="utf-8"))
    assert failure_payload["schema_version"] == "tinkerloop.failures.v1"
    assert failure_payload["summary"]["failed_scenario_ids"] == ["cleanup_preview_first_unit"]


def test_load_failed_scenario_ids_supports_report_directory(tmp_path):
    failed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="Preview the first cleanup unit",
                    checks=[
                        ScenarioCheck(type="assistant_contains_all", values=["missing substring"])
                    ],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )
    write_report([failed_result], output_dir=tmp_path, metadata={"adapter": {}})

    failed_ids = load_failed_scenario_ids(tmp_path)

    assert failed_ids == ["cleanup_preview_first_unit"]


def test_build_failure_artifact_uses_only_failed_results():
    passed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="Preview the first cleanup unit",
                    checks=[ScenarioCheck(type="assistant_contains_all", values=["Preview for"])],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )
    failed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="What should I clean first?",
                    checks=[
                        ScenarioCheck(type="assistant_contains_all", values=["missing substring"])
                    ],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )

    payload = build_failure_artifact(
        [passed_result, failed_result],
        metadata={"adapter": {}, "selected_runtime": {"provider": "bedrock", "model": "m1"}},
    )

    assert payload["summary"]["failed_scenario_count"] == 1
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_first_unit"]
    assert payload["summary"]["selected_runtime"]["model"] == "m1"


def test_build_diagnosis_artifact_is_compact_and_actionable():
    failed_result = run_scenario(
        Scenario(
            scenario_id="cleanup_first_unit",
            description="demo",
            turns=[
                ScenarioTurn(
                    user="What should I clean first?",
                    checks=[
                        ScenarioCheck(type="assistant_contains_all", values=["missing substring"])
                    ],
                )
            ],
        ),
        adapter=DummyAdapter(),
        user_id="u1",
    )

    payload = build_diagnosis_artifact(
        [failed_result],
        metadata={"adapter": {"name": "dummy"}, "preflight": {"status": "ready"}},
    )

    assert payload["schema_version"] == "tinkerloop.diagnosis.v1"
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_first_unit"]
    assert payload["summary"]["preflight_status"] == "ready"
    assert payload["diagnosis_items"][0]["scenario_id"] == "cleanup_first_unit"
    assert payload["diagnosis_items"][0]["turns"][0]["assistant_excerpt"]
    assert payload["rerun"]["scenario_ids"] == ["cleanup_first_unit"]


def test_run_scenarios_can_filter_by_tag():
    scenarios = [
        Scenario(
            scenario_id="cleanup_preview_first_unit",
            description="cleanup",
            tags=["cleanup", "preview"],
            turns=[
                ScenarioTurn(
                    user="Preview the first cleanup unit",
                    checks=[ScenarioCheck(type="assistant_contains_all", values=["Preview for"])],
                )
            ],
        ),
        Scenario(
            scenario_id="spam_review",
            description="spam",
            tags=["spam"],
            turns=[
                ScenarioTurn(
                    user="Check for spam",
                    checks=[ScenarioCheck(type="assistant_contains_all", values=["Preview for"])],
                )
            ],
        ),
    ]

    results = run_scenarios(
        scenarios,
        adapter=DummyAdapter(),
        user_id="u1",
        tag_filter={"cleanup"},
    )

    assert len(results) == 1
    assert results[0].scenario_id == "cleanup_preview_first_unit"
