# Architecture

## Core Pieces

### Engine

The engine owns:
- scenario loading
- turn execution
- deterministic checking
- result summarization
- JSON report generation

It does not know app-specific business logic.

### Adapter

The adapter is the only boundary between Tinkerloop and the target app.

Adapter responsibilities:
- preflight target readiness
- resolve the target app's inner orchestrator model from the target repo boundary
- apply explicit runtime selection when needed
- call the app's user-turn entrypoint
- expose trace recording around configured tool execution points
- provide optional metadata for reports

For stopgap local/staging integrations, the adapter may launch a target-owned runner command.
For long-term integrations, the target repo should expose a dedicated secure Tinkerloop driver contract.

### Scenario Files

Scenario files are JSON and define:
- `scenario_id`
- `description`
- `destructive`
- `turns`
- per-turn checks

### Reports

Reports are JSON artifacts with:
- run metadata
- turn transcripts
- tool traces
- check results
- pass/fail summary

## Current Adapter Model

The first adapter implementation is `PythonAppAdapter`.

It supports target apps that expose a Python callable such as:
- `handle_user_message(user_id=..., user_text=..., correlation_id=...)`

It can also patch target functions like `execute_tool(...)` to collect traces.

Current adapter contract also supports:
- `preflight(user_id=...)`
- `runtime_spec(user_id=...)`
- `runtime_candidates(user_id=...)`
- `select_runtime(runtime)`

The second adapter implementation is `CommandAppAdapter`.

It supports target-owned runner commands that:
- accept `user_id`, `user_text`, and `correlation_id`
- write the assistant reply to stdout
- optionally write tool traces to a file declared by `TINKERLOOP_TRACE_FILE`

This is the current Moppa stopgap path.

## Why This Shape

This keeps Tinkerloop:
- generic enough to reuse across apps
- concrete enough to be immediately useful
- small enough to audit and extend

## Security Direction

The long-term contract is stricter than the current stopgap.

Tinkerloop should eventually integrate with target repos through a fixed target-driver contract:
- target-owned
- non-prod only
- infrastructure-authenticated
- no arbitrary code execution
- no public backdoor endpoints

For AWS apps, the preferred direction is a dedicated non-prod driver function invoked through IAM.
