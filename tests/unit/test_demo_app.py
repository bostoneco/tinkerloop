from pathlib import Path

from tinkerloop.cli import load_adapter
from tinkerloop.engine import load_scenarios, run_scenarios


def test_demo_app_example_passes():
    repo_root = Path(__file__).resolve().parents[2]
    adapter = load_adapter("examples.demo_app.adapter:create_adapter")
    scenarios = load_scenarios(repo_root / "examples/demo_app/scenarios")

    results = run_scenarios(scenarios, adapter=adapter, user_id="demo-user")

    assert results
    assert all(result.passed for result in results)
