from __future__ import annotations

import io

import pytest

from tinkerloop.adapters.base import AppAdapter
from tinkerloop.cli import resolve_runtime_selection
from tinkerloop.models import RuntimeSpec


class DummyAdapter(AppAdapter):
    def __init__(
        self, *, resolved: RuntimeSpec | None = None, candidates: list[RuntimeSpec] | None = None
    ) -> None:
        self._resolved = resolved
        self._candidates = list(candidates or [])
        self.selected: RuntimeSpec | None = None

    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        return "ok"

    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        return self._resolved

    def runtime_candidates(self, *, user_id: str) -> list[RuntimeSpec]:
        return list(self._candidates)

    def select_runtime(self, runtime: RuntimeSpec) -> None:
        self.selected = runtime


def test_resolve_runtime_selection_uses_resolved_spec():
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="medium",
            reason="Resolved from defaults.",
        )
    )

    selected, metadata = resolve_runtime_selection(adapter=adapter, user_id="u1", interactive=False)

    assert selected.provider == "bedrock"
    assert adapter.selected == selected
    assert metadata["runtime_selection_mode"] == "resolved"


def test_resolve_runtime_selection_noninteractive_fails_with_candidates():
    adapter = DummyAdapter(
        candidates=[
            RuntimeSpec(
                provider="bedrock",
                model="us.amazon.nova-pro-v1:0",
                source="target_repo_defaults",
                confidence="medium",
                reason="Repo default.",
            ),
            RuntimeSpec(
                provider="gemini",
                model="gemini-2.5-flash",
                source="target_repo_supported_provider",
                confidence="low",
                reason="Alternate provider.",
            ),
        ]
    )

    with pytest.raises(RuntimeError) as exc:
        resolve_runtime_selection(adapter=adapter, user_id="u1", interactive=False)

    assert "Repo-derived candidates:" in str(exc.value)
    assert "bedrock / us.amazon.nova-pro-v1:0" in str(exc.value)


def test_resolve_runtime_selection_interactive_prompts_for_choice():
    adapter = DummyAdapter(
        candidates=[
            RuntimeSpec(
                provider="bedrock",
                model="us.amazon.nova-pro-v1:0",
                source="target_repo_defaults",
                confidence="medium",
                reason="Repo default.",
            ),
            RuntimeSpec(
                provider="gemini",
                model="gemini-2.5-flash",
                source="target_repo_supported_provider",
                confidence="low",
                reason="Alternate provider.",
            ),
        ]
    )
    output = io.StringIO()

    selected, metadata = resolve_runtime_selection(
        adapter=adapter,
        user_id="u1",
        interactive=True,
        input_func=lambda _prompt: "2",
        output_stream=output,
    )

    assert selected.provider == "gemini"
    assert adapter.selected == selected
    assert metadata["runtime_selection_mode"] == "interactive_candidate"
    assert "Select the inner runtime for the target app:" in output.getvalue()


def test_resolve_runtime_selection_provider_override_uses_matching_candidate():
    adapter = DummyAdapter(
        candidates=[
            RuntimeSpec(
                provider="bedrock",
                model="us.amazon.nova-pro-v1:0",
                source="target_repo_defaults",
                confidence="medium",
                reason="Repo default.",
            )
        ]
    )

    selected, metadata = resolve_runtime_selection(
        adapter=adapter,
        user_id="u1",
        inner_provider="bedrock",
        interactive=False,
    )

    assert selected.provider == "bedrock"
    assert selected.model == "us.amazon.nova-pro-v1:0"
    assert metadata["runtime_selection_mode"] == "override"
