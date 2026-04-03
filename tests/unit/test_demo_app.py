from pathlib import Path

from tinkerloop.cli import load_adapter
from tinkerloop.engine import load_scenarios, run_scenarios
from tinkerloop.models import RuntimeSpec


def test_demo_app_example_passes():
    repo_root = Path(__file__).resolve().parents[2]
    adapter = load_adapter(f"{repo_root / 'examples/demo_app/adapter.py'}:create_adapter")
    scenarios = load_scenarios(repo_root / "examples/demo_app/scenarios")

    results = run_scenarios(scenarios, adapter=adapter, user_id="demo-user")

    assert results
    assert all(result.passed for result in results)


def test_demo_app_adapter_exposes_fixed_runtime():
    repo_root = Path(__file__).resolve().parents[2]
    adapter = load_adapter(f"{repo_root / 'examples/demo_app/adapter.py'}:create_adapter")

    runtime = adapter.runtime_spec(user_id="demo-user")

    assert isinstance(runtime, RuntimeSpec)
    assert runtime.provider == "example"
    assert runtime.model == "demo-app"
