from __future__ import annotations

from tinkerloop.adapters import PythonAppAdapter
from tinkerloop.models import RuntimeSpec


class StarterTargetAdapter(PythonAppAdapter):
    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        return RuntimeSpec(
            provider="example",
            model="starter-target",
            source="example_adapter_defaults",
            confidence="high",
            reason="The starter target uses a fixed example runtime.",
        )


def create_adapter() -> PythonAppAdapter:
    return StarterTargetAdapter(
        handler_path="examples.starter_target.app:handle_user_message",
        patch_targets=["examples.starter_target.app:execute_tool"],
    )
