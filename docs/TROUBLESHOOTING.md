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
