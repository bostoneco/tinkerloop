import json

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.engine import (
    build_diagnosis_artifact,
    build_failure_artifact,
    build_report_payload,
    dict_contains,
    evaluate_checks,
    load_failed_scenario_ids,
    load_scenarios,
    run_scenario,
    run_scenarios,
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

    payload = build_report_payload([failed_result], metadata={"adapter": {"name": "dummy"}})

    assert payload["schema_version"] == "tinkerloop.report.v1"
    assert payload["summary"]["scenario_failed"] == 1
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_preview_first_unit"]
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

    payload = build_failure_artifact([passed_result, failed_result], metadata={"adapter": {}})

    assert payload["summary"]["failed_scenario_count"] == 1
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_first_unit"]


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

    payload = build_diagnosis_artifact([failed_result], metadata={"adapter": {"name": "dummy"}})

    assert payload["schema_version"] == "tinkerloop.diagnosis.v1"
    assert payload["summary"]["failed_scenario_ids"] == ["cleanup_first_unit"]
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
