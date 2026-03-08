from __future__ import annotations

import os
from pathlib import Path

from tinkerloop.adapters import PythonAppAdapter


DEFAULT_TRACE_TARGETS = [
    "src.orchestrator.loop:execute_tool",
    "src.orchestrator.providers.anthropic_provider:execute_tool",
    "src.orchestrator.providers.gemini_provider:execute_tool",
]


def create_adapter() -> PythonAppAdapter:
    repo_root = Path(
        os.environ.get(
            "TINKERLOOP_MOPPA_REPO",
            Path(__file__).resolve().parents[3] / "moppa",
        )
    ).resolve()
    return PythonAppAdapter(
        handler_path="src.orchestrator.loop:handle_user_message",
        patch_targets=DEFAULT_TRACE_TARGETS,
        repo_root=repo_root,
        env_files=[repo_root / ".env"],
    )
