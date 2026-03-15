from __future__ import annotations

import pytest

from tinkerloop.adapters import PythonAppAdapter


def test_python_app_adapter_records_tool_trace(tmp_path):
    target_file = tmp_path / "target_app.py"
    target_file.write_text(
        """
import json


def execute_tool(tool_name, user_id, arguments, correlation_id=None):
    return json.dumps({"status": "ok", "user_safe_summary": "Tool completed"})


def handle_user_message(*, user_id, user_text, correlation_id):
    execute_tool("cleanup", user_id, {"dry_run": True}, correlation_id=correlation_id)
    return "Preview ready"
""".strip(),
        encoding="utf-8",
    )

    adapter = PythonAppAdapter(
        handler_path="target_app:handle_user_message",
        patch_targets=["target_app:execute_tool"],
        repo_root=tmp_path,
    )

    with adapter.trace_recorder() as tracer:
        assistant = adapter.send_user_turn(
            user_id="u1",
            user_text="Preview the first cleanup unit",
            correlation_id="corr-1",
        )

    assert assistant == "Preview ready"
    assert len(tracer.calls) == 1
    assert tracer.calls[0].tool_name == "cleanup"
    assert tracer.calls[0].arguments == {"dry_run": True}
    assert tracer.calls[0].raw_result == {
        "status": "ok",
        "user_safe_summary": "Tool completed",
    }


def test_python_app_adapter_invalid_patch_target_fails_loudly(tmp_path):
    target_file = tmp_path / "target_app.py"
    target_file.write_text(
        """
def handle_user_message(*, user_id, user_text, correlation_id):
    return "Preview ready"
""".strip(),
        encoding="utf-8",
    )

    adapter = PythonAppAdapter(
        handler_path="target_app:handle_user_message",
        patch_targets=["missing.module:execute_tool"],
        repo_root=tmp_path,
    )

    with pytest.raises(ImportError):
        with adapter.trace_recorder():
            pass


def test_python_app_adapter_can_import_from_current_working_directory(monkeypatch, tmp_path):
    target_file = tmp_path / "cwd_target_app.py"
    target_file.write_text(
        """
import json


def execute_tool(tool_name, user_id, arguments, correlation_id=None):
    return json.dumps({"status": "ok", "user_safe_summary": "Tool completed"})


def handle_user_message(*, user_id, user_text, correlation_id):
    execute_tool("cleanup", user_id, {"dry_run": True}, correlation_id=correlation_id)
    return "Preview ready"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    adapter = PythonAppAdapter(
        handler_path="cwd_target_app:handle_user_message",
        patch_targets=["cwd_target_app:execute_tool"],
    )

    with adapter.trace_recorder() as tracer:
        assistant = adapter.send_user_turn(
            user_id="u1",
            user_text="Preview the first cleanup unit",
            correlation_id="corr-1",
        )

    assert assistant == "Preview ready"
    assert len(tracer.calls) == 1
