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
- trace tool calls by patching configured execution points
- evaluate deterministic checks
- write JSON reports for failures and regressions

Not in scope yet:
- automatic patch generation
- automatic deploys
- autonomous code changes without a human gate
- benchmark claims beyond the configured scenario set

## Quick Start

Install dev tooling and run the Moppa example:

```bash
python -m pytest -q
python -m tinkerloop.cli \
  --adapter examples.moppa.adapter:create_adapter \
  --user-id 5291202790 \
  --scenarios examples/moppa/scenarios
```

## Repo Layout

- `src/tinkerloop/`: reusable harness engine and adapter interfaces
- `examples/moppa/`: example adapter and example scenarios for Moppa
- `docs/`: charter, architecture, and MVP plan
- `tests/`: Tinkerloop unit tests

## Design Rules

- keep the core small and inspectable
- prefer deterministic checks before LLM judges
- keep target-app integration behind adapters
- no silent magic around tracing, patching, or scenario selection
- no automatic production actions
