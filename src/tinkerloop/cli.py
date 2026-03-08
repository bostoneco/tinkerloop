from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from tinkerloop.engine import load_scenarios, run_scenarios, summarize_results, write_report

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_adapter(factory_path: str):
    module_name, _, attr_name = factory_path.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid adapter factory path: {factory_path}")
    module = importlib.import_module(module_name)
    factory = getattr(module, attr_name)
    adapter = factory()
    return adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tinkerloop scenarios")
    parser.add_argument("--adapter", required=True, help="Adapter factory import path")
    parser.add_argument("--user-id", required=True)
    parser.add_argument(
        "--scenarios",
        default="examples/moppa/scenarios",
        help="Scenario file or directory",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Specific scenario id to run (repeatable)",
    )
    parser.add_argument(
        "--allow-destructive",
        action="store_true",
        help="Allow scenarios marked destructive",
    )
    parser.add_argument(
        "--report-dir",
        default="artifacts/reports",
        help="Where to write JSON reports",
    )
    args = parser.parse_args()

    adapter = load_adapter(args.adapter)
    scenarios = load_scenarios(args.scenarios)
    results = run_scenarios(
        scenarios,
        adapter=adapter,
        user_id=str(args.user_id),
        allow_destructive=bool(args.allow_destructive),
        scenario_filter=set(args.scenario) if args.scenario else None,
    )
    report_file = write_report(results, output_dir=args.report_dir, metadata=adapter.run_metadata())
    print(summarize_results(results))
    print(f"Report: {report_file}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
