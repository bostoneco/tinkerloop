# Tinkerloop

Tinkerloop is an eval-driven harness for testing and improving orchestrator-based apps through repeatable `test -> diagnose -> patch -> rerun` loops.

## Release Status

Tinkerloop is currently private and being prepared for a first public `alpha`
release.

What that means today:

- the package, CLI, adapters, and report artifacts are usable now
- the supported `v0.x` surface is documented in [`docs/STABILITY.md`](docs/STABILITY.md)
- the project is intended for technically strong early adopters who can own a target adapter
- the project is not yet positioned as a benchmark suite or production-assurance layer

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

## Who It Is For

- teams that already have a target app and want deterministic scenario-based regression loops
- teams that can keep target-specific logic in a target-owned adapter and scenario library
- teams that want report-driven reruns rather than broad benchmark claims

## Who It Is Not For

- users looking for a zero-config app framework
- teams that need remote secure-driver support today
- users who want Tinkerloop to measure general model quality

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
- rerun only failed scenarios from report artifacts

Not in scope yet:
- automatic patch generation
- automatic deploys
- autonomous code changes without a human gate
- benchmark claims beyond the configured scenario set
- secure non-prod target-driver contracts

## Quick Start

Install from a GitHub release wheel:

```bash
python -m pip install https://github.com/bostoneco/tinkerloop/releases/download/<tag>/tinkerloop-<version>-py3-none-any.whl
```

Then run it against a target-owned adapter and scenario directory:

```bash
tinkerloop \
  run \
  --adapter /path/to/target_adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/scenarios
```

For local development from a source checkout, install editable mode and use the in-repo demo target:

```bash
python -m pip install -e .[dev]
python -m pytest -q
tinkerloop \
  run \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/scenarios

# fuller demo target
tinkerloop \
  run \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios
```

For real projects, the target repo should own its adapter and scenarios.
`--adapter` accepts either an import path such as `your_project.tinkerloop_adapter:create_adapter` or a file path such as `/path/to/target_adapter.py:create_adapter`.

If the adapter cannot resolve one inner model confidently, Tinkerloop will prompt for a repo-derived candidate in interactive mode. In non-interactive mode, pass explicit overrides:

```bash
tinkerloop \
  run \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --inner-provider <provider> \
  --inner-model <model>
```

Rerun only failed scenarios from report artifacts:

```bash
tinkerloop \
  run \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --failed-from artifacts/reports
```

Run only a tagged feature slice:

```bash
tinkerloop \
  run \
  --adapter examples/demo_app/adapter.py:create_adapter \
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

## Docs Map

- [`docs/STABILITY.md`](docs/STABILITY.md): supported `v0.x` surface and experimental boundaries
- [`docs/QUICKSTART_TARGET_REPO.md`](docs/QUICKSTART_TARGET_REPO.md): minimal target-owned integration path
- [`docs/ADAPTER_GUIDE.md`](docs/ADAPTER_GUIDE.md): when to use `PythonAppAdapter` vs `CommandAppAdapter`
- [`docs/TRUST_MODEL.md`](docs/TRUST_MODEL.md): what a pass/fail result does and does not mean
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): first-run failure modes
- [`docs/WORKED_EXAMPLE.md`](docs/WORKED_EXAMPLE.md): failure -> diagnosis -> rerun example
- [`docs/WORKING_AGREEMENT.md`](docs/WORKING_AGREEMENT.md): day-to-day run discipline
- [`docs/TARGET_CONTRACT.md`](docs/TARGET_CONTRACT.md): public integration boundary

## Support Matrix

- Python: `3.12`
- Adapter shapes: `PythonAppAdapter`, `CommandAppAdapter`
- Report schemas: `tinkerloop.report.v1`, `tinkerloop.failures.v1`, `tinkerloop.diagnosis.v1`
- Check types: `assistant_contains_all`, `assistant_contains_any`, `assistant_not_contains`, `tool_used`, `tool_call_count_at_most`, `tool_call_matches`

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
