# Trust Model

Tinkerloop validates deterministic scenario conformance for a target app under
a specific adapter, target state, and runtime selection.

It does not validate general model quality.
It does not create a benchmark by itself.

## What A Passing Run Means

A passing run means:

- the target completed the scenario turns
- the configured deterministic checks passed
- the observed tool path matched what the checks required
- the adapter reported whatever run metadata it implements for that execution

For `tinkerloop run`, a passing repair run is still provisional until the
confirmation loop passes. Check `confirmation_status` in
`latest-diagnosis.json`.

## What A Passing Run Does Not Mean

A passing run does not prove:

- broad assistant quality
- safety outside the covered scenario set
- cross-model comparability
- production readiness
- that the latest repair result has been confirmed against the real target agent

## Supported Deterministic Checks

- `assistant_contains_all`
- `assistant_contains_any`
- `assistant_not_contains`
- `tool_used`
- `tool_call_count_at_most`
- `tool_call_matches`

Each check is intentionally narrow.
If a behavior matters, encode it explicitly in scenarios rather than inferring
it from a broad pass/fail label.

Scenario files are validated before execution.
Unsupported check types, empty turn sets, and empty `user` prompts are definition
errors, not target-runtime failures.

## When Results Are Comparable

Treat two runs as comparable only when all of these are held constant:

- scenario set
- adapter implementation
- target repo state
- target environment/config state
- selected runtime provider/model

If any of those change, treat the runs as different experimental conditions.
If `run_metadata()` does not record enough context to confirm that, treat the
comparison as weak evidence.

## Actionable Failure vs Uncertain Failure

Failures are actionable when:

- preflight is clean
- runtime selection is explicit or confidently resolved
- the failing deterministic check clearly names the mismatch

Failures are uncertain when:

- preflight is blocked
- runtime selection is ambiguous
- trace capture is missing or obviously incomplete

In uncertain cases, fix adapter/runtime fidelity first.

## Smoke Reproducibility Note

Alpha smoke runs on March 14, 2026 used the bundled demo target,
the same scenario directory, and the same fixed example runtime
(`provider=example`, `model=demo-app`).

| Run | Scenario total | Passed | Failed |
| --- | --- | --- | --- |
| 1 | 2 | 2 | 0 |
| 2 | 2 | 2 | 0 |
| 3 | 2 | 2 | 0 |

This is a smoke-level stability check for the bundled example only.
It is not a benchmark and should not be generalized to other targets.
