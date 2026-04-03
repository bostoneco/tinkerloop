---
name: tinkerloop-runner
description: Run Tinkerloop and triage results. Use when asked to execute scenarios, rerun failures, inspect report artifacts, or drive a narrow-first test -> diagnose -> patch -> rerun loop against a target app.
---

# Tinkerloop Runner

Use this skill for day-to-day loop execution and failure triage.

Start with:
- `docs/WORKING_AGREEMENT.md`
- `README.md`
- `src/tinkerloop/cli.py`

## Default loop

Actor boundary:
- the outer coding model may patch and rerun
- the inner target orchestrator is the system under test
- do not let the outer coding model satisfy scenarios directly

1. Confirm preflight and runtime selection first.
2. Run the smallest valid slice with `--scenario` or `--tag`.
3. Inspect artifacts, not just terminal output:
   - `latest.json`
   - `latest-failures.json`
   - `latest-diagnosis.json`
4. Fix one bounded cause.
5. Rerun the failing slice.
6. Rerun the failed set from report artifacts with `--failed-from`.
7. Finish with the broader regression slice that matches the change.
8. If the real target agent matters, run `tinkerloop confirm ...` as the final gate.

## Canonical commands

Narrow first:

```bash
tinkerloop run \
  --adapter /path/to/target/adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/target/scenarios \
  --tag <tag>
```

Confirmation gate:

```bash
tinkerloop confirm \
  --adapter /path/to/target/adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/target/scenarios \
  --non-interactive
```

Rerun the failed set from report artifacts:

```bash
tinkerloop run \
  --adapter /path/to/target/adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/target/scenarios \
  --failed-from /path/to/report-or-report-dir
```

If runtime resolution is ambiguous in non-interactive mode, pass explicit `--inner-provider` and `--inner-model`.

## Triage standard

For each failure, capture:
- symptom from `latest-diagnosis.json`
- failing deterministic check
- observed tool path or assistant behavior
- likely owner: adapter, prompt, routing, or product logic
- exact rerun command for the next iteration

Do not widen scope until the narrow rerun is understood.
