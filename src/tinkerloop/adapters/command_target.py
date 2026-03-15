from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.adapters.env_files import parse_env_file
from tinkerloop.models import ToolTrace


class FileTraceRecorder(TraceRecorder):
    def __init__(self, adapter: "CommandAppAdapter") -> None:
        super().__init__()
        self._adapter = adapter
        self._trace_file: Path | None = None

    def __enter__(self) -> "FileTraceRecorder":
        fd, raw_path = tempfile.mkstemp(prefix="tinkerloop-trace-", suffix=".json")
        os.close(fd)
        self._trace_file = Path(raw_path)
        self._adapter._active_trace_file = self._trace_file
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._trace_file and self._trace_file.is_file():
                payload = json.loads(self._trace_file.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    self.calls = [ToolTrace(**item) for item in payload if isinstance(item, dict)]
        finally:
            self._adapter._active_trace_file = None
            if self._trace_file:
                self._trace_file.unlink(missing_ok=True)
        return None


class CommandAppAdapter(AppAdapter):
    def __init__(
        self,
        *,
        command_builder: Callable[[str, str, str], list[str]],
        workdir: str | Path,
        env_files: list[str | Path] | None = None,
        env_overrides: dict[str, str] | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.command_builder = command_builder
        self.workdir = Path(workdir).resolve()
        self.env_files = [Path(item).resolve() for item in (env_files or [])]
        self.env_overrides = dict(env_overrides or {})
        self.timeout_seconds = int(timeout_seconds)
        self._active_trace_file: Path | None = None

    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        command = self.command_builder(user_id, user_text, correlation_id)
        env = self._build_env()
        if self._active_trace_file:
            env["TINKERLOOP_TRACE_FILE"] = str(self._active_trace_file)
        completed = subprocess.run(
            command,
            cwd=self.workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(detail or f"Target command failed with exit code {completed.returncode}")
        return completed.stdout.strip()

    def trace_recorder(self) -> TraceRecorder:
        return FileTraceRecorder(self)

    def run_metadata(self) -> dict[str, object]:
        return {
            "adapter": type(self).__name__,
            "workdir": str(self.workdir),
            "timeout_seconds": self.timeout_seconds,
        }

    def _build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        for env_file in self.env_files:
            env.update(parse_env_file(env_file))
        env.update(self.env_overrides)
        return env
