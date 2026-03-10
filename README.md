# Tinkerloop

Tinkerloop is an eval-driven harness for testing and improving orchestrator-based apps through repeatable `test -> diagnose -> patch -> rerun` loops.

## What It Is

Tinkerloop is not another app-specific bot framework.
It is a reusable outer loop for systems that already have:
- an inner orchestrator model
- tool or MCP integrations
- a conversational or API-facing entrypoint

Tinkerloop plays the role of:
- user simulator
- integration tester
- trajectory recorder
- deterministic judge
- developer feedback loop driver

## MVP Scope

Current MVP:
- load multi-turn scenario files
- run them against a target app adapter
- preflight the target app before scenario execution
- resolve the target app's inner runtime from the target repo boundary
- trace tool calls by patching configured execution points
- trace tool calls from target-owned runner commands
- evaluate deterministic checks
- write JSON reports for failures and regressions
- rerun only failed scenarios from a prior report

Not in scope yet:
- automatic patch generation
- automatic deploys
- autonomous code changes without a human gate
- benchmark claims beyond the configured scenario set
- secure non-prod target-driver contracts

## Quick Start

Install dev tooling and run the generic demo target:

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m tinkerloop.cli \
  --adapter examples.demo_app.adapter:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios
```

For real projects, the target repo should own its adapter and scenarios.
`--adapter` accepts either an import path such as `your_project.tinkerloop_adapter:create_adapter` or a file path such as `/path/to/target_adapter.py:create_adapter`.

If the adapter cannot resolve one inner model confidently, Tinkerloop will prompt for a repo-derived candidate in interactive mode. In non-interactive mode, pass explicit overrides:

```bash
PYTHONPATH=src python -m tinkerloop.cli \
  --adapter examples.demo_app.adapter:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --inner-provider <provider> \
  --inner-model <model>
```

Rerun only previously failed scenarios:

```bash
PYTHONPATH=src python -m tinkerloop.cli \
  --adapter examples.demo_app.adapter:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --failed-from artifacts/reports
```

Run only a tagged feature slice:

```bash
PYTHONPATH=src python -m tinkerloop.cli \
  --adapter examples.demo_app.adapter:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --tag cleanup \
  --tag preview
```

Artifacts written on each run:
- timestamped report: `tinkerloop-<timestamp>.json`
- stable latest report: `latest.json`
- stable failure summary: `latest-failures.json`
- stable diagnosis payload: `latest-diagnosis.json`

Day-to-day usage conventions live in `docs/WORKING_AGREEMENT.md`.
The public integration boundary is documented in `docs/TARGET_CONTRACT.md`.

## Repo Layout

- `src/tinkerloop/`: reusable harness engine and adapter interfaces
- `examples/`: optional example and transition fixtures
- `docs/`: charter, architecture, target contract, MVP plan, implementation handoff, and working agreement
- `tests/`: Tinkerloop unit tests

## Design Rules

- keep the core small and inspectable
- prefer deterministic checks before LLM judges
- keep target-app integration behind adapters
- no silent magic around tracing, patching, or scenario selection
- no automatic production actions
- future target-driver integrations must be non-prod only and secure by default
