# Target Contract

Tinkerloop is implemented in Python, but the target app under test does not need to be.

The public boundary is the target contract.
Each target app should own its own Tinkerloop integration in the target repo.

The CLI can load an adapter through:
- an import path such as `your_project.tinkerloop_adapter:create_adapter`
- a file path such as `/path/to/target_adapter.py:create_adapter`

## Local Adapter Contract

The current local contract is the `AppAdapter` surface:

- `preflight(user_id=...)`
- `runtime_spec(user_id=...)`
- `runtime_candidates(user_id=...)`
- `select_runtime(runtime)`
- `send_user_turn(user_id=..., user_text=..., correlation_id=...)`
- `trace_recorder()`
- `run_metadata()`

Responsibilities:
- verify target readiness before a run
- resolve the target runtime from the target repo boundary
- invoke the target app entrypoint
- capture tool traces from the real execution path
- provide enough metadata to explain what environment was exercised

## Target-Owned Responsibility

Target-specific code belongs in the target repo, not in Tinkerloop.

That includes:
- auth and readiness checks
- target env/config names
- business rules
- target scenario libraries
- target runner scripts
- target deployment logic

## Integration Shapes

Tinkerloop currently supports two local integration shapes:

- Python callable target through `PythonAppAdapter`
- target-owned runner command through `CommandAppAdapter`

The target app can be written in any language as long as it exposes one of these boundaries or a future driver contract.

## Future Remote Driver Contract

The long-term language-neutral contract should look like:

- `preflight`
- `start_session`
- `send_turn`
- `poll_events`
- `get_trace`

That contract should be:
- target-owned
- non-prod only
- infrastructure-authenticated
- auditable
- fixed-surface rather than arbitrary code execution

## OSS Positioning

Tinkerloop should be presented as:
- a Python reference runtime
- a language-neutral target contract
- a reusable outer-loop harness for orchestrator and MCP-style apps

It should not require target apps to be Python.
