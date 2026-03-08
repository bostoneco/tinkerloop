import json

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.engine import (
    dict_contains,
    evaluate_checks,
    load_scenarios,
    run_scenario,
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
