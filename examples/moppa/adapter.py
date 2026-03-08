from __future__ import annotations

import os
import re
from pathlib import Path

from tinkerloop.adapters import PythonAppAdapter
from tinkerloop.models import PreflightResult, RuntimeSpec


DEFAULT_TRACE_TARGETS = [
    "src.orchestrator.loop:execute_tool",
    "src.orchestrator.providers.anthropic_provider:execute_tool",
    "src.orchestrator.providers.gemini_provider:execute_tool",
]


class MoppaAdapter(PythonAppAdapter):
    def __init__(self, *, repo_root: Path) -> None:
        super().__init__(
            handler_path="src.orchestrator.loop:handle_user_message",
            patch_targets=DEFAULT_TRACE_TARGETS,
            repo_root=repo_root,
            env_files=[repo_root / ".env"],
        )
        self._selected_runtime: RuntimeSpec | None = None

    def preflight(self, *, user_id: str) -> PreflightResult:
        self._prepare()
        if not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_CONNECTION_STRING")):
            return PreflightResult(
                status="blocked_config",
                summary="Moppa database configuration is missing. Set DATABASE_URL or POSTGRES_CONNECTION_STRING in the target repo environment.",
            )

        try:
            user = self._load_moppa_user(user_id)
        except Exception as exc:
            return PreflightResult(
                status="blocked_runtime",
                summary=f"Moppa user lookup failed: {type(exc).__name__}: {exc}",
            )

        if not user:
            return PreflightResult(
                status="blocked_runtime",
                summary=f"Moppa user `{user_id}` was not found in the target repo runtime.",
                details={"user_id": user_id},
            )

        if not user.get("gmail_tokens"):
            return PreflightResult(
                status="blocked_auth",
                summary=f"Moppa user `{user_id}` is not connected to Gmail. Connect the account in Moppa first, then rerun Tinkerloop.",
                details={"user_id": user_id},
            )

        try:
            creds = self._load_moppa_gmail_credentials(user_id)
        except Exception as exc:
            return PreflightResult(
                status="blocked_runtime",
                summary=f"Moppa Gmail credential check failed: {type(exc).__name__}: {exc}",
            )

        if not creds:
            return PreflightResult(
                status="blocked_auth",
                summary=f"Moppa could not load usable Gmail credentials for user `{user_id}`. Reconnect Gmail in Moppa, then rerun Tinkerloop.",
                details={"user_id": user_id},
            )

        return PreflightResult(
            status="ready",
            summary=f"Moppa user `{user_id}` is connected and ready.",
            details={
                "user_id": user_id,
                "email": user.get("username") or user.get("email") or "",
                "status": user.get("status") or "",
            },
        )

    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        env_values = self._read_env_values()
        provider_value = (
            os.environ.get("MOPPA_MODEL_PROVIDER") or env_values.get("MOPPA_MODEL_PROVIDER") or ""
        ).strip()
        model_value = (
            os.environ.get("MOPPA_CHAT_MODEL") or env_values.get("MOPPA_CHAT_MODEL") or ""
        ).strip()

        default_provider = self._repo_default_provider()
        default_models = self._repo_default_models()
        known_providers = set(default_models)

        normalized_provider = self._normalize_provider(provider_value) if provider_value else ""
        provider_known = normalized_provider in known_providers
        inferred_provider = self._infer_provider_from_model(model_value)

        if provider_value and model_value:
            if not provider_known:
                return None
            if inferred_provider and inferred_provider != normalized_provider:
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
        env_values = self._read_env_values()
        provider_value = (
            os.environ.get("MOPPA_MODEL_PROVIDER") or env_values.get("MOPPA_MODEL_PROVIDER") or ""
        ).strip()
        model_value = (
            os.environ.get("MOPPA_CHAT_MODEL") or env_values.get("MOPPA_CHAT_MODEL") or ""
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
        os.environ["MOPPA_MODEL_PROVIDER"] = runtime.provider
        os.environ["MOPPA_CHAT_MODEL"] = runtime.model
        self._selected_runtime = runtime

    def run_metadata(self) -> dict[str, object]:
        metadata = super().run_metadata()
        if self._selected_runtime:
            metadata["selected_runtime"] = {
                "provider": self._selected_runtime.provider,
                "model": self._selected_runtime.model,
                "source": self._selected_runtime.source,
                "confidence": self._selected_runtime.confidence,
                "reason": self._selected_runtime.reason,
            }
        return metadata

    def _load_moppa_user(self, user_id: str):
        return self._load_target_attr("src.storage.user_facade:get_user")(user_id)

    def _load_moppa_gmail_credentials(self, user_id: str):
        return self._load_target_attr("src.utils.auth:get_gmail_credentials")(user_id)

    def _repo_default_provider(self) -> str:
        loop_path = (self.repo_root or Path.cwd()) / "src/orchestrator/loop.py"
        text = loop_path.read_text(encoding="utf-8")
        match = re.search(r'MOPPA_MODEL_PROVIDER",\s*"([^"]+)"', text)
        return self._normalize_provider(match.group(1)) if match else ""

    def _repo_default_models(self) -> dict[str, str]:
        repo_root = self.repo_root or Path.cwd()
        bedrock_default = self._extract_default_model(
            repo_root / "src/orchestrator/providers/anthropic_provider.py"
        )
        gemini_default = self._extract_default_model(
            repo_root / "src/orchestrator/providers/gemini_provider.py"
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


def create_adapter() -> MoppaAdapter:
    repo_root = Path(
        os.environ.get(
            "TINKERLOOP_MOPPA_REPO",
            Path(__file__).resolve().parents[3] / "moppa",
        )
    ).resolve()
    return MoppaAdapter(repo_root=repo_root)
