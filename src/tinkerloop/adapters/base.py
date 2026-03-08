from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any

from tinkerloop.models import PreflightResult, RuntimeSpec, ToolTrace


class TraceRecorder(AbstractContextManager["TraceRecorder"]):
    def __init__(self) -> None:
        self.calls: list[ToolTrace] = []

    def __enter__(self) -> "TraceRecorder":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class AppAdapter(ABC):
    @abstractmethod
    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        raise NotImplementedError

    def preflight(self, *, user_id: str) -> PreflightResult:
        return PreflightResult(status="ready", summary="Adapter is ready.")

    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        return None

    def runtime_candidates(self, *, user_id: str) -> list[RuntimeSpec]:
        return []

    def select_runtime(self, runtime: RuntimeSpec) -> None:
        return None

    def trace_recorder(self) -> TraceRecorder:
        return TraceRecorder()

    def run_metadata(self) -> dict[str, Any]:
        return {}
