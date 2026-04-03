# Troubleshooting

## Adapter Import Fails

Symptoms:

- `Invalid adapter factory path`
- `Could not import module`
- `Adapter module file not found`

Checks:

- confirm the value is `<module-or-file>:<factory>`
- if you use a file path, confirm the file exists
- if you use an import path, confirm the target repo is importable from the current environment

## Preflight Blocks The Run

Symptoms:

- CLI exits early with a report and a blocked summary

Checks:

- read the `preflight` section in `latest.json`
- fix auth/config/runtime readiness in the target-owned adapter

## Runtime Selection Is Ambiguous

Symptoms:

- non-interactive runs fail with candidate choices

Checks:

- pass `--inner-provider` and `--inner-model`
- make sure the adapter can derive candidates only from the target repo boundary

## No Scenarios Were Selected

Symptoms:

- `No scenarios were selected to run.`
- `No scenarios matched the current selection`

Checks:

- confirm the scenario path exists
- confirm `--tag` and `--scenario` filters match real files
- confirm destructive scenarios are enabled only when needed

## Tool Traces Are Missing

Symptoms:

- tool-based checks fail unexpectedly
- `tool_trace_count` is `0`

Checks:

- for `PythonAppAdapter`, confirm `patch_targets` point at the real tool call site and that the patched callable uses `(tool_name, user_id, arguments, correlation_id=None)`
- for `CommandAppAdapter`, confirm the target command writes `TINKERLOOP_TRACE_FILE`
- prefer tracing the real execution path instead of a wrapper function

## `--failed-from` Does Not Work

Checks:

- point it at a report file or report directory
- confirm the directory contains `latest-failures.json`, `latest.json`, or a timestamped report

## Repair Run Passed But Still Looks Provisional

Symptoms:

- `tinkerloop run` exits with code `3`
- the CLI prints `Repair loop passed. Run tinkerloop confirm to validate with the real inner model. Without confirmation, these results do not prove agent quality.`
- the summary includes a `NOTE:` about confirmation
- `latest-diagnosis.json` shows `confirmation_status` as `missing` or `stale`

Checks:

- run `tinkerloop confirm ...` against the intended target boundary
- if the target repo has a more realistic runner or adapter, use that for `confirm`
- do not treat the green repair run as final until confirmation passes

## Confirmation Was Blocked By Infra

Symptoms:

- `tinkerloop confirm` exits with code `2`
- `confirm-latest-diagnosis.json` shows `confirmation_status` as `blocked`
- the diagnosis metadata includes `preflight_error`

Checks:

- inspect the preflight error first
- fix model access, credentials, network reachability, or adapter readiness
- rerun `tinkerloop confirm ...` after the blocked dependency is restored
