from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from tinkerloop.adapters.base import AppAdapter, TraceRecorder
from tinkerloop.adapters.env_files import load_env_file
from tinkerloop.models import ToolTrace


class ToolPatchRecorder(TraceRecorder):
    def __init__(self, patch_targets: list[str]) -> None:
        super().__init__()
        self._patch_targets = patch_targets
        self._patches: list[tuple[object, str, Any]] = []

    def __enter__(self) -> "ToolPatchRecorder":
        for patch_target in self._patch_targets:
            module, attr_name, original = _load_module_attr(patch_target, label="patch target")
            if not callable(original):
                raise TypeError(f"Patch target is not callable: {patch_target}")

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
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        if self.repo_root and str(self.repo_root) not in sys.path:
            sys.path.insert(0, str(self.repo_root))
        for env_file in self.env_files:
            load_env_file(env_file)
        self._handler = self._resolve_callable(self.handler_path)
        self._prepared = True

    @staticmethod
    def _resolve_callable(import_path: str) -> Callable[..., str]:
        _, _, target = _load_module_attr(import_path, label="handler path")
        if not callable(target):
            raise TypeError(f"Import path is not callable: {import_path}")
        return target


def _load_module_attr(import_path: str, *, label: str) -> tuple[object, str, Any]:
    module_name, _, attr_name = import_path.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid {label}: {import_path}")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(f"Could not import module `{module_name}` for {label} `{import_path}`.") from exc
    try:
        target = getattr(module, attr_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Module `{module_name}` does not define `{attr_name}` for {label} `{import_path}`."
        ) from exc
    return module, attr_name, target
