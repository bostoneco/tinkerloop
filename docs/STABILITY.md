# Stability And Support

Tinkerloop is in **alpha**. This document defines the contract for the initial `v0.x` line.

## Supported In `v0.x`

- Python `3.10+`
- local CLI execution through `tinkerloop`
- CLI commands `run` and `confirm`
- target-owned adapters loaded by import path or file path
- `PythonAppAdapter`
- `CommandAppAdapter`
- scenario JSON fields:
  - `scenario_id`
  - `description`
  - `tags`
  - `destructive`
  - `turns[].user`
  - `turns[].checks`
- report artifacts:
  - `latest.json`
  - `latest-failures.json`
  - `latest-diagnosis.json`
  - `confirm-latest.json`
  - `confirm-latest-failures.json`
  - `confirm-latest-diagnosis.json`
- report schema versions:
  - `tinkerloop.report.v1`
  - `tinkerloop.failures.v1`
  - `tinkerloop.diagnosis.v1`

## Supported Check Types

- `assistant_contains_all`
- `assistant_contains_any`
- `assistant_not_contains`
- `tool_used`
- `tool_call_count_at_most`
- `tool_call_matches`

## Experimental Or Subject To Change

- future secure remote-driver contract
- outer developer patch/apply loop
- any LLM-judge behavior
- any benchmark or cross-target quality claim
- any schema change beyond the `v1` artifacts listed above

## Support Position

For the current `alpha`, Tinkerloop is intended for technically strong
early adopters who can own their target adapter and scenario library.
It is not yet positioned as a broadly supported evaluation platform.
