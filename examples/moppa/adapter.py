from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from tinkerloop.adapters import CommandAppAdapter
from tinkerloop.models import PreflightResult, RuntimeSpec


class MoppaAdapter(CommandAppAdapter):
    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root
        self._selected_runtime: RuntimeSpec | None = None
        self._repo_env = self._read_env_file(repo_root / ".env")
        runner = repo_root / "scripts/tinkerloop_turn.py"
        python_bin = repo_root / ".venv/bin/python"
        super().__init__(
            command_builder=lambda user_id, user_text, correlation_id: [
                str(python_bin),
                str(runner),
                "--user-id",
                user_id,
                "--correlation-id",
                correlation_id,
                "--message",
                user_text,
            ],
            workdir=repo_root,
            env_files=[repo_root / ".env"],
            env_overrides=self._default_env_overrides(repo_root),
            timeout_seconds=90,
        )

    def preflight(self, *, user_id: str) -> PreflightResult:
        api_base = self._api_base_url()
        if not api_base:
            return PreflightResult(
                status="blocked_config",
                summary="Moppa API_BASE_URL is missing in the target repo environment.",
            )
        runner = self.repo_root / "scripts/tinkerloop_turn.py"
        if not runner.is_file():
            return PreflightResult(
                status="blocked_config",
                summary=f"Moppa runner script is missing: {runner}",
            )
        python_bin = self.repo_root / ".venv/bin/python"
        if not python_bin.is_file():
            return PreflightResult(
                status="blocked_config",
                summary=f"Moppa virtualenv is missing: {python_bin}",
            )

        mailbox = self._proxy_tool("mailbox", user_id, {"scope": "overview"})
        status = str(mailbox.get("status") or "")
        if status == "ok":
            return PreflightResult(
                status="ready",
                summary=f"Moppa user `{user_id}` is connected and ready through deployed tool proxy.",
                details={"user_id": user_id, "api_base_url": api_base},
            )
        if status in {"failed_auth", "error"}:
            error_text = str(mailbox.get("error") or "")
            if "No Gmail credentials" in error_text or status == "failed_auth":
                return PreflightResult(
                    status="blocked_auth",
                    summary=(
                        f"Moppa could not load Gmail credentials for `{user_id}` via deployed tool proxy. "
                        "For the current stopgap path, use a Moppa MCP-connected user id and complete Gmail OAuth for that user first."
                    ),
                    details={"user_id": user_id, "api_base_url": api_base},
                )
        return PreflightResult(
            status="blocked_runtime",
            summary=(
                f"Moppa readiness check failed for `{user_id}`: "
                f"{mailbox.get('user_safe_summary') or mailbox.get('error') or status or 'unknown error'}"
            ),
            details={"user_id": user_id, "api_base_url": api_base, "payload": mailbox},
        )

    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        provider_value = (
            os.environ.get("MOPPA_MODEL_PROVIDER")
            or self._repo_env.get("MOPPA_MODEL_PROVIDER")
            or ""
        ).strip()
        model_value = (
            os.environ.get("MOPPA_CHAT_MODEL") or self._repo_env.get("MOPPA_CHAT_MODEL") or ""
        ).strip()

        default_provider = self._repo_default_provider()
        default_models = self._repo_default_models()
        known_providers = set(default_models)

        normalized_provider = self._normalize_provider(provider_value) if provider_value else ""
        provider_known = normalized_provider in known_providers
        inferred_provider = self._infer_provider_from_model(model_value)

        if provider_value and model_value:
            if not provider_known or (inferred_provider and inferred_provider != normalized_provider):
                return None
            return RuntimeSpec(
                provider=normalized_provider,
                model=model_value,
                source="target_runtime_env",
                confidence="high",
                reason="Resolved from target repo provider and model configuration.",
                details={"configured_provider": provider_value or normalized_provider},
            )

        if provider_value:
            if not provider_known:
                return None
            return RuntimeSpec(
                provider=normalized_provider,
                model=default_models[normalized_provider],
                source="target_env_plus_repo_default",
                confidence="high",
                reason="Resolved provider from target runtime config and model from target repo code default.",
                details={"configured_provider": provider_value or normalized_provider},
            )

        if model_value:
            if not inferred_provider:
                return None
            return RuntimeSpec(
                provider=inferred_provider,
                model=model_value,
                source="target_runtime_env",
                confidence="high",
                reason="Resolved model from target runtime config and inferred provider from the configured model name.",
            )

        if default_provider and default_provider in default_models:
            return RuntimeSpec(
                provider=default_provider,
                model=default_models[default_provider],
                source="target_repo_defaults",
                confidence="medium",
                reason="Resolved from target repo code defaults.",
            )

        return None

    def runtime_candidates(self, *, user_id: str) -> list[RuntimeSpec]:
        provider_value = (
            os.environ.get("MOPPA_MODEL_PROVIDER")
            or self._repo_env.get("MOPPA_MODEL_PROVIDER")
            or ""
        ).strip()
        model_value = (
            os.environ.get("MOPPA_CHAT_MODEL") or self._repo_env.get("MOPPA_CHAT_MODEL") or ""
        ).strip()
        default_provider = self._repo_default_provider()
        default_models = self._repo_default_models()

        candidates: list[RuntimeSpec] = []
        inferred_provider = self._infer_provider_from_model(model_value)
        normalized_provider = self._normalize_provider(provider_value) if provider_value else ""

        if model_value and inferred_provider:
            candidates.append(
                RuntimeSpec(
                    provider=inferred_provider,
                    model=model_value,
                    source="target_runtime_env",
                    confidence="medium",
                    reason="Model was configured in the target runtime env and provider was inferred from the model name.",
                )
            )

        if normalized_provider and normalized_provider in default_models:
            candidates.append(
                RuntimeSpec(
                    provider=normalized_provider,
                    model=default_models[normalized_provider],
                    source="target_env_plus_repo_default",
                    confidence="medium",
                    reason="Provider was configured in the target runtime env and model comes from the target repo default for that provider.",
                )
            )

        if default_provider and default_provider in default_models:
            candidates.append(
                RuntimeSpec(
                    provider=default_provider,
                    model=default_models[default_provider],
                    source="target_repo_defaults",
                    confidence="medium",
                    reason="This is the target repo default runtime.",
                )
            )

        for provider_name in ("bedrock", "gemini"):
            model_name = default_models.get(provider_name)
            if not model_name:
                continue
            candidates.append(
                RuntimeSpec(
                    provider=provider_name,
                    model=model_name,
                    source="target_repo_supported_provider",
                    confidence="low" if provider_name != default_provider else "medium",
                    reason="Supported by target repo provider defaults.",
                )
            )

        deduped: list[RuntimeSpec] = []
        seen: set[tuple[str, str]] = set()
        for candidate in candidates:
            key = (candidate.provider, candidate.model)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def select_runtime(self, runtime: RuntimeSpec) -> None:
        self.env_overrides["MOPPA_MODEL_PROVIDER"] = runtime.provider
        self.env_overrides["MOPPA_CHAT_MODEL"] = runtime.model
        self._selected_runtime = runtime

    def run_metadata(self) -> dict[str, object]:
        metadata = super().run_metadata()
        metadata["repo_root"] = str(self.repo_root)
        metadata["api_base_url"] = self._api_base_url()
        if self._selected_runtime:
            metadata["selected_runtime"] = {
                "provider": self._selected_runtime.provider,
                "model": self._selected_runtime.model,
                "source": self._selected_runtime.source,
                "confidence": self._selected_runtime.confidence,
                "reason": self._selected_runtime.reason,
            }
        return metadata

    def _proxy_tool(self, tool_name: str, user_id: str, args: dict[str, object]) -> dict[str, object]:
        body = json.dumps({"tool_name": tool_name, "user_id": user_id, "args": args}).encode()
        req = urllib.request.Request(
            f"{self._api_base_url().rstrip('/')}/mcp/tool",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read().decode()
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode()
        try:
            data = json.loads(payload)
            return data if isinstance(data, dict) else {"status": "error", "error": "invalid_payload"}
        except json.JSONDecodeError:
            return {"status": "error", "error": "invalid_payload", "user_safe_summary": payload[:300]}

    def _api_base_url(self) -> str:
        return (
            os.environ.get("API_BASE_URL")
            or self.env_overrides.get("API_BASE_URL")
            or self._repo_env.get("API_BASE_URL")
            or ""
        ).strip()

    def _default_env_overrides(self, repo_root: Path) -> dict[str, str]:
        overrides = {
            "DATABASE_URL": f"sqlite:///{repo_root / '.tinkerloop_local.db'}",
            "MOPPA_DEBUG_SKIP_FASTPATH": "1",
            "TINKERLOOP_LOCAL_PROXY_MODE": "1",
        }
        api_base = (self._repo_env.get("API_BASE_URL") or "").strip()
        if api_base:
            overrides["API_BASE_URL"] = api_base
        aws_profile = (self._repo_env.get("AWS_PROFILE") or "").strip()
        if aws_profile:
            overrides["AWS_PROFILE"] = aws_profile
        return overrides

    def _repo_default_provider(self) -> str:
        loop_path = self.repo_root / "src/orchestrator/loop.py"
        text = loop_path.read_text(encoding="utf-8")
        match = re.search(r'MOPPA_MODEL_PROVIDER",\s*"([^"]+)"', text)
        return self._normalize_provider(match.group(1)) if match else ""

    def _repo_default_models(self) -> dict[str, str]:
        bedrock_default = self._extract_default_model(
            self.repo_root / "src/orchestrator/providers/anthropic_provider.py"
        )
        gemini_default = self._extract_default_model(
            self.repo_root / "src/orchestrator/providers/gemini_provider.py"
        )
        models: dict[str, str] = {}
        if bedrock_default:
            models["bedrock"] = bedrock_default
        if gemini_default:
            models["gemini"] = gemini_default
        return models

    @staticmethod
    def _extract_default_model(path: Path) -> str:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8")
        match = re.search(r'DEFAULT_MODEL\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else ""

    @staticmethod
    def _normalize_provider(value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "anthropic":
            return "bedrock"
        return normalized

    @staticmethod
    def _infer_provider_from_model(model: str) -> str:
        normalized = model.strip().lower()
        if not normalized:
            return ""
        if "gemini" in normalized:
            return "gemini"
        if (
            normalized.startswith("us.amazon.")
            or "nova" in normalized
            or normalized.startswith("anthropic.")
        ):
            return "bedrock"
        return ""

    @staticmethod
    def _read_env_file(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        if not path.is_file():
            return values
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
        return values


def create_adapter() -> MoppaAdapter:
    repo_root = Path(
        os.environ.get("TINKERLOOP_MOPPA_REPO", Path(__file__).resolve().parents[3] / "moppa")
    ).resolve()
    return MoppaAdapter(repo_root=repo_root)
