from __future__ import annotations

import json
from pathlib import Path

from tinkerloop.adapters.command_target import CommandAppAdapter


def test_command_adapter_runs_command_and_collects_trace(tmp_path: Path):
    script = tmp_path / "runner.py"
    script.write_text(
        """
import json
import os
import pathlib
import sys

trace_file = os.environ.get("TINKERLOOP_TRACE_FILE")
if trace_file:
    pathlib.Path(trace_file).write_text(json.dumps([{
        "tool_name": "cleanup",
        "arguments": {"dry_run": True},
        "correlation_id": sys.argv[2],
        "duration_ms": 7,
        "status": "ok",
        "user_safe_summary": "Dry run",
        "raw_result": {"status": "ok"}
    }]), encoding="utf-8")
print(f"reply:{sys.argv[1]}")
        """.strip(),
        encoding="utf-8",
    )

    adapter = CommandAppAdapter(
        command_builder=lambda user_id, user_text, correlation_id: [
            "python",
            str(script),
            user_text,
            correlation_id,
        ],
        workdir=tmp_path,
    )

    with adapter.trace_recorder() as tracer:
        assistant = adapter.send_user_turn(
            user_id="u1",
            user_text="hello",
            correlation_id="corr-1",
        )

    assert assistant == "reply:hello"
    assert len(tracer.calls) == 1
    assert tracer.calls[0].tool_name == "cleanup"
    assert tracer.calls[0].arguments["dry_run"] is True


def test_command_adapter_merges_env_files_and_overrides(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VALUE=from_env\nKEEP=1\n", encoding="utf-8")
    script = tmp_path / "runner.py"
    script.write_text(
        """
import json
import os
print(json.dumps({"value": os.environ.get("VALUE"), "keep": os.environ.get("KEEP")}))
        """.strip(),
        encoding="utf-8",
    )

    adapter = CommandAppAdapter(
        command_builder=lambda user_id, user_text, correlation_id: ["python", str(script)],
        workdir=tmp_path,
        env_files=[env_file],
        env_overrides={"VALUE": "override"},
    )

    assistant = adapter.send_user_turn(user_id="u1", user_text="x", correlation_id="corr-2")
    payload = json.loads(assistant)

    assert payload == {"value": "override", "keep": "1"}


def test_command_adapter_run_metadata_includes_env_context(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VALUE=from_env\n", encoding="utf-8")

    adapter = CommandAppAdapter(
        command_builder=lambda user_id, user_text, correlation_id: ["python", "-c", "print('ok')"],
        workdir=tmp_path,
        env_files=[env_file],
        env_overrides={"VALUE": "override", "KEEP": "1"},
        timeout_seconds=30,
    )

    metadata = adapter.run_metadata()

    assert metadata["workdir"] == str(tmp_path.resolve())
    assert metadata["timeout_seconds"] == 30
    assert metadata["env_files"] == [str(env_file.resolve())]
    assert metadata["env_override_keys"] == ["KEEP", "VALUE"]
