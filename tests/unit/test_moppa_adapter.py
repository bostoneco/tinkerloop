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
    (repo_root / "scripts").mkdir(parents=True)
    (repo_root / ".venv/bin").mkdir(parents=True)
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
    (repo_root / "scripts/tinkerloop_turn.py").write_text("print('ok')\n", encoding="utf-8")
    (repo_root / ".venv/bin/python").write_text("", encoding="utf-8")
    (repo_root / ".env").write_text("\n".join(env_lines or []), encoding="utf-8")
    return repo_root


def test_moppa_adapter_preflight_blocks_when_api_base_missing(tmp_path):
    adapter = MoppaAdapter(repo_root=_make_repo(tmp_path))

    result = adapter.preflight(user_id="u1")

    assert result.status == "blocked_config"
    assert "API_BASE_URL" in result.summary


def test_moppa_adapter_preflight_blocks_when_gmail_missing(monkeypatch, tmp_path):
    adapter = MoppaAdapter(
        repo_root=_make_repo(tmp_path, env_lines=["API_BASE_URL=https://example.com/dev"])
    )
    monkeypatch.setattr(
        adapter,
        "_proxy_tool",
        lambda tool_name, user_id, args: {
            "status": "error",
            "error": "No Gmail credentials for user u1",
        },
    )

    result = adapter.preflight(user_id="u1")

    assert result.status == "blocked_auth"
    assert "MCP-connected user id" in result.summary


def test_moppa_adapter_preflight_ready(monkeypatch, tmp_path):
    adapter = MoppaAdapter(
        repo_root=_make_repo(tmp_path, env_lines=["API_BASE_URL=https://example.com/dev"])
    )
    monkeypatch.setattr(
        adapter,
        "_proxy_tool",
        lambda tool_name, user_id, args: {"status": "ok", "data": {}},
    )

    result = adapter.preflight(user_id="u1")

    assert result.status == "ready"
    assert result.details["api_base_url"] == "https://example.com/dev"


def test_moppa_adapter_runtime_spec_uses_explicit_env(monkeypatch, tmp_path):
    repo_root = _make_repo(
        tmp_path,
        env_lines=[
            "API_BASE_URL=https://example.com/dev",
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
    adapter = MoppaAdapter(
        repo_root=_make_repo(tmp_path, env_lines=["API_BASE_URL=https://example.com/dev"])
    )
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
        env_lines=[
            "API_BASE_URL=https://example.com/dev",
            "MOPPA_MODEL_PROVIDER=unknown-provider",
        ],
    )
    adapter = MoppaAdapter(repo_root=repo_root)
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    candidates = adapter.runtime_candidates(user_id="u1")

    assert len(candidates) >= 2
    assert candidates[0].provider == "bedrock"
    assert any(candidate.provider == "gemini" for candidate in candidates)


def test_moppa_adapter_select_runtime_sets_target_env(tmp_path, monkeypatch):
    adapter = MoppaAdapter(
        repo_root=_make_repo(tmp_path, env_lines=["API_BASE_URL=https://example.com/dev"])
    )
    runtime = adapter.runtime_spec(user_id="u1")

    assert runtime is not None
    monkeypatch.delenv("MOPPA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MOPPA_CHAT_MODEL", raising=False)

    adapter.select_runtime(runtime)

    assert adapter.run_metadata()["selected_runtime"]["provider"] == "bedrock"
