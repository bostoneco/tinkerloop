# Actor Model

Tinkerloop has two distinct model roles:

- inner target orchestrator:
  the model and tool path inside the app under test
- outer coding model:
  the developer tool model using Tinkerloop artifacts to diagnose, patch, and rerun

The inner target orchestrator is the system under test.
The outer coding model is the operator of the improvement loop.

## Valid Loop

The valid Tinkerloop cycle is:

1. run the target app through its adapter boundary
2. inspect Tinkerloop artifacts
3. patch the target repo
4. rerun the target app through the same adapter boundary

The outer coding model can act between runs.
It must not replace the inner target orchestrator during a measured run.

## Invalid Loop

A run is invalid if the coding model:

- satisfies the scenario directly with its own tool loop
- bypasses the target adapter boundary
- produces a result without exercising the target app's real orchestrator path

If that happens, the result does not describe the target app.
It describes the outer coding model instead.

## Two-Stage Workflow

Tinkerloop supports two explicit run intents:

- `tinkerloop run ...`
  repair loop against the target adapter
- `tinkerloop confirm ...`
  external confirmation loop after a candidate fix looks good

Use `run` to iterate quickly.
Use `confirm` to validate that the real target agent can still operate after the fix.
That is strongest when the confirmation run points at a more realistic target-owned runner or adapter boundary.

## Artifact Separation

Repair loop artifacts:

- `latest.json`
- `latest-failures.json`
- `latest-diagnosis.json`

Confirmation loop artifacts:

- `confirm-latest.json`
- `confirm-latest-failures.json`
- `confirm-latest-diagnosis.json`

Keep these separate.
A green repair loop is not a final pass.
A successful `tinkerloop run` exits with code `3` until `tinkerloop confirm`
passes against the real inner model.
A green confirmation loop is the stronger acceptance signal.
`latest-diagnosis.json` now includes `confirmation_status` so coding models can
see that gap directly.

## Agent Guidance

When using a coding tool such as Codex, Claude Code, or Copilot:

- run Tinkerloop as a harness
- patch the target repo between runs
- do not emulate the target orchestrator
- prefer a target-owned wrapper command when available
- use `--non-interactive` in unattended runs
- treat a repair-loop warning about missing or stale confirmation as a real gap, not noise
