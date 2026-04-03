from pathlib import Path

from tinkerloop.cli import load_adapter
from tinkerloop.engine import load_scenarios, run_scenarios
from tinkerloop.models import RuntimeSpec


def test_starter_target_example_passes():
    repo_root = Path(__file__).resolve().parents[2]
    adapter = load_adapter(f"{repo_root / 'examples/starter_target/adapter.py'}:create_adapter")
    scenarios = load_scenarios(repo_root / "examples/starter_target/scenarios")

    results = run_scenarios(scenarios, adapter=adapter, user_id="demo-user")

    assert results
    assert all(result.passed for result in results)


def test_starter_target_adapter_exposes_fixed_runtime():
    repo_root = Path(__file__).resolve().parents[2]
    adapter = load_adapter(f"{repo_root / 'examples/starter_target/adapter.py'}:create_adapter")

    runtime = adapter.runtime_spec(user_id="demo-user")

    assert isinstance(runtime, RuntimeSpec)
    assert runtime.provider == "example"
    assert runtime.model == "starter-target"
