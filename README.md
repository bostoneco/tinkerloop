# Tinkerloop

Tinkerloop helps you improve AI agents with a scenario-based loop: reproduce the failure, diagnose it with deterministic checks, patch the target, and rerun until the behavior matches what you expect.

It is a scenario-based harness for improving AI agents through repeatable repair and confirmation loops.

## Release Status

Tinkerloop is in **alpha**.

- The package, CLI, adapters, and report artifacts are usable now.
- The supported `v0.x` surface is documented in [`docs/STABILITY.md`](docs/STABILITY.md).
- The project is intended for technically strong early adopters who can own a target adapter.
- It is not yet positioned as a benchmark suite or production-assurance layer.

## What It Is

Tinkerloop is not another app-specific bot framework.
It is a reusable outer loop for AI agent systems that already have:
- an inner orchestrator model
- tool or MCP integrations
- a conversational or API-facing entrypoint

Tinkerloop plays the role of:
- user simulator
- integration tester
- trajectory recorder
- deterministic judge
- developer feedback loop driver

## Actor Model

There are two distinct roles in a Tinkerloop workflow:

- inner target orchestrator:
  the model and tool path inside the app under test
- outer coding model:
  the developer tool model using Tinkerloop artifacts to patch and rerun

The outer coding model may analyze results and edit code between runs.
It must not replace the inner target orchestrator during a measured run.
See [`docs/ACTOR_MODEL.md`](docs/ACTOR_MODEL.md).

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
- separate repair-loop and confirmation-loop runs

Not in scope yet:
- automatic patch generation
- automatic deploys
- autonomous code changes without a human gate
- benchmark claims beyond the configured scenario set
- secure non-prod target-driver contracts

## Quick Start

Tinkerloop supports **Python 3.10+**. This repo pins `3.12.9` in [`.python-version`](.python-version) for local development with `pyenv`.

The PyPI distribution name is `tinkerloop-ai`. Install it with:

```bash
python3 -m pip install tinkerloop-ai
```

If you need to install directly from a GitHub release asset instead:

```bash
python3 -m pip install https://github.com/bostoneco/tinkerloop/releases/download/<tag>/tinkerloop_ai-<version>-py3-none-any.whl
```

Then run it against a target-owned adapter and scenario directory:

```bash
tinkerloop \
  run \
  --adapter /path/to/target_adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/scenarios
```

`tinkerloop run` exits with code `3` when the repair loop passes.
That is intentional: run `tinkerloop confirm ...` before treating the result as final.

When a candidate fix looks good, run the external confirmation loop:

```bash
tinkerloop \
  confirm \
  --adapter /path/to/target_adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/scenarios \
  --non-interactive
```

If your target repo exposes a more realistic runner or adapter for real-agent validation,
use that boundary for `confirm` instead of the faster repair-loop boundary.

For local development from a source checkout:

```bash
pyenv local 3.12.9
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
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

For `PythonAppAdapter`, each `patch_targets` entry should point at a callable with
the standard tool-call shape
`(tool_name, user_id, arguments, correlation_id=None)`.
Scenario files must contain at least one turn, and each turn must define a
non-empty `user` prompt.

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
  includes `confirmation_status` for repair-loop vs confirmation-loop visibility,
  including blocked or failed prior confirmation attempts
- confirmation timestamped report: `confirm-tinkerloop-<timestamp>.json`
- confirmation latest report: `confirm-latest.json`
- confirmation failure summary: `confirm-latest-failures.json`
- confirmation diagnosis payload: `confirm-latest-diagnosis.json`

When a repair run passes, Tinkerloop exits with code `3` and tells you to run
`tinkerloop confirm ...`.
Repair-only results do not prove agent quality.
If confirmation is blocked, Tinkerloop still writes
`confirm-latest-diagnosis.json` with `confirmation_status: "blocked"` and the
preflight error so the attempt is visible in artifacts.

## Docs Map

- [`docs/STABILITY.md`](docs/STABILITY.md): supported `v0.x` surface and experimental boundaries
- [`docs/ACTOR_MODEL.md`](docs/ACTOR_MODEL.md): inner target orchestrator vs outer coding model roles
- [`docs/QUICKSTART_TARGET_REPO.md`](docs/QUICKSTART_TARGET_REPO.md): minimal target-owned integration path
- [`docs/ADAPTER_GUIDE.md`](docs/ADAPTER_GUIDE.md): when to use `PythonAppAdapter` vs `CommandAppAdapter`
- [`docs/TRUST_MODEL.md`](docs/TRUST_MODEL.md): what a pass/fail result does and does not mean
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): first-run failure modes
- [`docs/WORKED_EXAMPLE.md`](docs/WORKED_EXAMPLE.md): failure -> diagnosis -> rerun example
- [`docs/WORKING_AGREEMENT.md`](docs/WORKING_AGREEMENT.md): day-to-day run discipline
- [`docs/TARGET_CONTRACT.md`](docs/TARGET_CONTRACT.md): public integration boundary

## Support Matrix

- Python: `3.10+`
- Commands: `run`, `confirm`
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

## License

Apache License 2.0. See [LICENSE](LICENSE). Business-friendly: use, modify, and distribute with minimal conditions; includes a patent grant.

## Contributing

PRs are accepted from maintainers and invited contributors only. For bugs or ideas, open an [issue](https://github.com/bostoneco/tinkerloop/issues). See [CONTRIBUTING.md](CONTRIBUTING.md).
