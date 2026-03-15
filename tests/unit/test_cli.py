from __future__ import annotations

import io
from pathlib import Path

import pytest

from tinkerloop.__about__ import __version__
from tinkerloop.adapters.base import AppAdapter
from tinkerloop.cli import load_adapter, main, resolve_runtime_selection
from tinkerloop.models import PreflightResult, RuntimeSpec, Scenario, ScenarioTurn


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

    def preflight(self, *, user_id: str) -> PreflightResult:
        return PreflightResult(status="ready", summary="ready")


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


def test_load_adapter_supports_file_path(tmp_path):
    adapter_file = tmp_path / "target_adapter.py"
    adapter_file.write_text(
        """
from tinkerloop.adapters.base import AppAdapter
from tinkerloop.models import PreflightResult


class FileAdapter(AppAdapter):
    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        return "ok"

    def preflight(self, *, user_id: str) -> PreflightResult:
        return PreflightResult(status="ready", summary="ready")


def create_adapter():
    return FileAdapter()
""".strip(),
        encoding="utf-8",
    )

    adapter = load_adapter(f"{adapter_file}:create_adapter")

    assert type(adapter).__name__ == "FileAdapter"


def test_load_adapter_supports_import_path_from_current_working_directory(monkeypatch, tmp_path):
    package_dir = tmp_path / "target_pkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "adapter.py").write_text(
        """
from tinkerloop.adapters.base import AppAdapter
from tinkerloop.models import PreflightResult, RuntimeSpec


class ImportAdapter(AppAdapter):
    def send_user_turn(self, *, user_id: str, user_text: str, correlation_id: str) -> str:
        return "ok"

    def preflight(self, *, user_id: str) -> PreflightResult:
        return PreflightResult(status="ready", summary="ready")

    def runtime_spec(self, *, user_id: str) -> RuntimeSpec | None:
        return RuntimeSpec(
            provider="example",
            model="cwd-import",
            source="test",
            confidence="high",
            reason="test",
        )


def create_adapter():
    return ImportAdapter()
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    adapter = load_adapter("target_pkg.adapter:create_adapter")

    assert type(adapter).__name__ == "ImportAdapter"


def test_main_uses_failed_from_to_filter_scenarios(monkeypatch, tmp_path):
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="high",
            reason="Resolved.",
        )
    )
    captured = {}
    monkeypatch.setattr(
        "tinkerloop.cli.load_adapter",
        lambda _factory_path: adapter,
    )
    monkeypatch.setattr(
        "tinkerloop.cli.load_scenarios",
        lambda _path: [
            Scenario(
                scenario_id="cleanup_preview_first_unit",
                description="demo",
                turns=[ScenarioTurn(user="Preview the first cleanup unit")],
            )
        ],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.load_failed_scenario_ids",
        lambda _path: ["cleanup_preview_first_unit"],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.run_scenarios",
        lambda scenarios, *, adapter, user_id, allow_destructive, scenario_filter, tag_filter: captured.update(
            {"scenario_filter": scenario_filter, "tag_filter": tag_filter}
        )
        or [],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.write_report",
        lambda results, *, output_dir, metadata=None: Path(output_dir) / "latest.json",
    )
    exit_code = main(
        [
            "run",
            "--adapter",
            "tests.fixtures.sample_adapter:create_adapter",
            "--user-id",
            "u1",
            "--scenarios",
            str(tmp_path),
            "--failed-from",
            str(tmp_path),
            "--report-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["scenario_filter"] == {"cleanup_preview_first_unit"}
    assert captured["tag_filter"] is None


def test_main_passes_tag_filter(monkeypatch, tmp_path):
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="high",
            reason="Resolved.",
        )
    )
    captured = {}
    monkeypatch.setattr("tinkerloop.cli.load_adapter", lambda _factory_path: adapter)
    monkeypatch.setattr(
        "tinkerloop.cli.load_scenarios",
        lambda _path: [
            Scenario(
                scenario_id="cleanup_preview_first_unit",
                description="demo",
                turns=[ScenarioTurn(user="Preview the first cleanup unit")],
                tags=["cleanup", "preview"],
            )
        ],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.run_scenarios",
        lambda scenarios, *, adapter, user_id, allow_destructive, scenario_filter, tag_filter: (
            captured.update({"tag_filter": tag_filter}) or []
        ),
    )
    monkeypatch.setattr(
        "tinkerloop.cli.write_report",
        lambda results, *, output_dir, metadata=None: Path(output_dir) / "latest.json",
    )
    exit_code = main(
        [
            "run",
            "--adapter",
            "tests.fixtures.sample_adapter:create_adapter",
            "--user-id",
            "u1",
            "--scenarios",
            str(tmp_path),
            "--tag",
            "cleanup",
            "--tag",
            "preview",
            "--report-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["tag_filter"] == {"cleanup", "preview"}


def test_main_accepts_run_subcommand(monkeypatch, tmp_path):
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="high",
            reason="Resolved.",
        )
    )
    captured = {}
    monkeypatch.setattr("tinkerloop.cli.load_adapter", lambda _factory_path: adapter)
    monkeypatch.setattr(
        "tinkerloop.cli.load_scenarios",
        lambda _path: [
            Scenario(
                scenario_id="cleanup_preview_first_unit",
                description="demo",
                turns=[ScenarioTurn(user="Preview the first cleanup unit")],
            )
        ],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.run_scenarios",
        lambda scenarios, *, adapter, user_id, allow_destructive, scenario_filter, tag_filter: (
            captured.update({"user_id": user_id, "scenario_filter": scenario_filter}) or []
        ),
    )
    monkeypatch.setattr(
        "tinkerloop.cli.write_report",
        lambda results, *, output_dir, metadata=None: Path(output_dir) / "latest.json",
    )

    exit_code = main(
        [
            "run",
            "--adapter",
            "tests.fixtures.sample_adapter:create_adapter",
            "--user-id",
            "u1",
            "--scenarios",
            str(tmp_path),
            "--report-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["user_id"] == "u1"
    assert captured["scenario_filter"] is None


def test_main_fails_when_no_scenarios_loaded(monkeypatch, tmp_path, capsys):
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="high",
            reason="Resolved.",
        )
    )
    monkeypatch.setattr("tinkerloop.cli.load_adapter", lambda _factory_path: adapter)
    monkeypatch.setattr("tinkerloop.cli.load_scenarios", lambda _path: [])
    monkeypatch.setattr(
        "tinkerloop.cli.write_report",
        lambda results, *, output_dir, metadata=None: Path(output_dir) / "latest.json",
    )
    exit_code = main(
        [
            "run",
            "--adapter",
            "tests.fixtures.sample_adapter:create_adapter",
            "--user-id",
            "u1",
            "--scenarios",
            str(tmp_path),
            "--report-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 2
    assert "No scenarios were selected to run." in capsys.readouterr().err


def test_main_fails_when_filters_select_no_scenarios(monkeypatch, tmp_path, capsys):
    adapter = DummyAdapter(
        resolved=RuntimeSpec(
            provider="bedrock",
            model="us.amazon.nova-pro-v1:0",
            source="target_repo_defaults",
            confidence="high",
            reason="Resolved.",
        )
    )
    monkeypatch.setattr("tinkerloop.cli.load_adapter", lambda _factory_path: adapter)
    monkeypatch.setattr(
        "tinkerloop.cli.load_scenarios",
        lambda _path: [
            Scenario(
                scenario_id="cleanup_preview_first_unit",
                description="demo",
                turns=[ScenarioTurn(user="Preview the first cleanup unit")],
                tags=["cleanup"],
            )
        ],
    )
    monkeypatch.setattr(
        "tinkerloop.cli.write_report",
        lambda results, *, output_dir, metadata=None: Path(output_dir) / "latest.json",
    )
    exit_code = main(
        [
            "run",
            "--adapter",
            "tests.fixtures.sample_adapter:create_adapter",
            "--user-id",
            "u1",
            "--scenarios",
            str(tmp_path),
            "--tag",
            "preview",
            "--report-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 2
    assert "No scenarios matched the current selection" in capsys.readouterr().err


def test_main_prints_version_and_exits(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["tinkerloop", "--version"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert f"tinkerloop {__version__}" in capsys.readouterr().out


def test_main_help_lists_run_command(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "run" in output
    assert "Use `tinkerloop run ...` to execute scenarios." in output


def test_main_rejects_flag_only_invocation(capsys):
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--adapter",
                "tests.fixtures.sample_adapter:create_adapter",
                "--user-id",
                "u1",
                "--scenarios",
                "scenarios",
            ]
        )

    assert exc.value.code == 2
    assert "Missing command `run`" in capsys.readouterr().err
