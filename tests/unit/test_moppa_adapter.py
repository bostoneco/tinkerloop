from __future__ import annotations

from pathlib import Path

from examples.moppa.adapter import MoppaAdapter


def _make_repo(
    tmp_path: Path,
    *,
    loop_default: str = "bedrock",
    bedrock_model: str = "us.amazon.nova-pro-v1:0",
    gemini_model: str = "gemini-2.5-flash",
    env_lines: list[str] | None = None,
) -> Path:
    repo_root = tmp_path / "moppa"
    (repo_root / "src/orchestrator/providers").mkdir(parents=True)
    (repo_root / "src/orchestrator/loop.py").write_text(
        f'provider = os.environ.get("MOPPA_MODEL_PROVIDER", "{loop_default}")\n',
        encoding="utf-8",
    )
    (repo_root / "src/orchestrator/providers/anthropic_provider.py").write_text(
        f'DEFAULT_MODEL = "{bedrock_model}"\n',
        encoding="utf-8",
    )
    (repo_root / "src/orchestrator/providers/gemini_provider.py").write_text(
        f'DEFAULT_MODEL = "{gemini_model}"\n',
        encoding="utf-8",
    )
    (repo_root / ".env").write_text("\n".join(env_lines or []), encoding="utf-8")
    return repo_root


def test_moppa_adapter_preflight_blocks_when_user_missing(monkeypatch, tmp_path):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))
    monkeypatch.setattr(adapter, "_prepare", lambda: None)
    monkeypatch.setattr(adapter, "_load_moppa_user", lambda _user_id: None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")

    result = adapter.preflight(user_id="u1")

    assert result.status == "blocked_runtime"
    assert "was not found" in result.summary


def test_moppa_adapter_preflight_blocks_when_gmail_missing(monkeypatch, tmp_path):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))
    monkeypatch.setattr(adapter, "_prepare", lambda: None)
    monkeypatch.setattr(
        adapter,
        "_load_moppa_user",
        lambda _user_id: {"status": "new", "gmail_tokens": ""},
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")

    result = adapter.preflight(user_id="u1")

    assert result.status == "blocked_auth"
    assert "not connected to Gmail" in result.summary


def test_moppa_adapter_preflight_ready(monkeypatch, tmp_path):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))
    monkeypatch.setattr(adapter, "_prepare", lambda: None)
    monkeypatch.setattr(
        adapter,
        "_load_moppa_user",
        lambda _user_id: {"status": "connected", "gmail_tokens": "{}", "email": "user@example.com"},
    )
    monkeypatch.setattr(adapter, "_load_moppa_gmail_credentials", lambda _user_id: object())
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")

    result = adapter.preflight(user_id="u1")

    assert result.status == "ready"
    assert result.details["email"] == "user@example.com"


def test_moppa_adapter_runtime_spec_uses_explicit_env(monkeypatch, tmp_path):
    repo_root = _make_repo(
        tmp_path,
        env_lines=[
            "MOPPA_MODEL_PROVIDER=gemini",
            "MOPPA_CHAT_MODEL=gemini-3-flash-preview",
        ],
    )
    adapter = MoppaAdapter(repo_root=repo_root)
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    runtime = adapter.runtime_spec(user_id="u1")

    assert runtime is not None
    assert runtime.provider == "gemini"
    assert runtime.model == "gemini-3-flash-preview"
    assert runtime.confidence == "high"


def test_moppa_adapter_runtime_spec_falls_back_to_repo_defaults(monkeypatch, tmp_path):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    runtime = adapter.runtime_spec(user_id="u1")

    assert runtime is not None
    assert runtime.provider == "bedrock"
    assert runtime.model == "us.amazon.nova-pro-v1:0"
    assert runtime.source == "target_repo_defaults"


def test_moppa_adapter_runtime_candidates_include_repo_matches(monkeypatch, tmp_path):
    repo_root = _make_repo(
        tmp_path,
        env_lines=["MOPPA_MODEL_PROVIDER=unknown-provider"],
    )
    adapter = MoppaAdapter(repo_root=repo_root)
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    candidates = adapter.runtime_candidates(user_id="u1")

    assert len(candidates) >= 2
    assert candidates[0].provider == "bedrock"
    assert any(candidate.provider == "gemini" for candidate in candidates)


def test_moppa_adapter_select_runtime_sets_target_env(tmp_path, monkeypatch):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))
    runtime = adapter.runtime_spec(user_id="u1")

    assert runtime is not None
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    adapter.select_runtime(runtime)

    assert adapter.run_metadata()["selected_runtime"]["provider"] == "bedrock"
