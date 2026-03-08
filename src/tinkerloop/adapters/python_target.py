from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.models import ToolTrace


class ToolPatchRecorder(TraceRecorder):
    def __init__(self, patch_targets: list[str]) -> None:
        super().__init__()
        self._patch_targets = patch_targets
        self._patches: list[tuple[object, str, Any]] = []

    def __enter__(self) -> "ToolPatchRecorder":
        for patch_target in self._patch_targets:
            module_name, _, attr_name = patch_target.rpartition(":")
            if not module_name or not attr_name:
                continue
            try:
                module = importlib.import_module(module_name)
                original = getattr(module, attr_name)
            except Exception:
                continue

            def wrapped(
                tool_name: str,
                user_id: str,
                arguments: dict[str, Any] | None,
                correlation_id=None,
                *,
                _original=original,
            ):
                started = time.time()
                result = _original(tool_name, user_id, arguments, correlation_id=correlation_id)
                duration_ms = int((time.time() - started) * 1000)
                parsed: dict[str, Any] | str
                status: str | None = None
                user_safe_summary: str | None = None
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, dict):
                        status = str(parsed.get("status") or "") or None
                        user_safe_summary = str(parsed.get("user_safe_summary") or "") or None
                    else:
                        parsed = result
                except Exception:
                    parsed = result
                self.calls.append(
                    ToolTrace(
                        tool_name=tool_name,
                        arguments=dict(arguments or {}),
                        correlation_id=correlation_id,
                        duration_ms=duration_ms,
                        status=status,
                        user_safe_summary=user_safe_summary,
                        raw_result=parsed,
                    )
                )
                return result

            self._patches.append((module, attr_name, original))
            setattr(module, attr_name, wrapped)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        while self._patches:
            module, attr_name, original = self._patches.pop()
            setattr(module, attr_name, original)
        return None


class PythonAppAdapter(AppAdapter):
    def __init__(
        self,
        *,
        handler_path: str,
        patch_targets: list[str] | None = None,
        repo_root: str | Path | None = None,
        env_files: list[str | Path] | None = None,
    ) -> None:
        self.handler_path = handler_path
        self.patch_targets = list(patch_targets or [])
        self.repo_root = Path(repo_root).resolve() if repo_root else None
        self.env_files = [Path(item).resolve() for item in (env_files or [])]
        self._prepared = False
        self._handler: Callable[..., str] | None = None

    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        self._prepare()
        assert self._handler is not None
        return self._handler(user_id=user_id, user_text=user_text, correlation_id=correlation_id)

    def trace_recorder(self) -> TraceRecorder:
        self._prepare()
        return ToolPatchRecorder(self.patch_targets)

    def run_metadata(self) -> dict[str, Any]:
        return {
            "adapter": type(self).__name__,
            "handler_path": self.handler_path,
            "repo_root": str(self.repo_root) if self.repo_root else "",
        }

    def _prepare(self) -> None:
        if self._prepared:
            return
        if self.repo_root and str(self.repo_root) not in sys.path:
            sys.path.insert(0, str(self.repo_root))
        for env_file in self.env_files:
            self._load_env_file(env_file)
        self._handler = self._resolve_callable(self.handler_path)
        self._prepared = True

    @staticmethod
    def _resolve_callable(import_path: str) -> Callable[..., str]:
        module_name, _, attr_name = import_path.partition(":")
        if not module_name or not attr_name:
            raise ValueError(f"Invalid import path: {import_path}")
        module = importlib.import_module(module_name)
        target = getattr(module, attr_name)
        if not callable(target):
            raise TypeError(f"Import path is not callable: {import_path}")
        return target

    @staticmethod
    def _load_env_file(path: Path) -> None:
        if not path.is_file():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
