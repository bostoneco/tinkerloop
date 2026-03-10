from __future__ import annotations

from tinkerloop.adapters import PythonAppAdapter


def create_adapter() -> PythonAppAdapter:
    return PythonAppAdapter(
        handler_path="examples.demo_app.app:handle_user_message",
        patch_targets=["examples.demo_app.app:execute_tool"],
    )
