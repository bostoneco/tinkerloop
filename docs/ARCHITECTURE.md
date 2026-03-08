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
- call the app's user-turn entrypoint
- expose trace recording around configured tool execution points
- provide optional metadata for reports

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

## Why This Shape

This keeps Tinkerloop:
- generic enough to reuse across apps
- concrete enough to be immediately useful
- small enough to audit and extend
