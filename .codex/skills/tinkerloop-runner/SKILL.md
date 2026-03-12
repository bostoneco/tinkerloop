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

1. Confirm preflight and runtime selection first.
2. Run the smallest valid slice with `--scenario` or `--tag`.
3. Inspect artifacts, not just terminal output:
   - `latest.json`
   - `latest-failures.json`
   - `latest-diagnosis.json`
4. Fix one bounded cause.
5. Rerun the failing slice.
6. Rerun the prior failed set with `--failed-from`.
7. Finish with the broader regression slice that matches the change.

## Canonical commands

Narrow first:

```bash
PYTHONPATH=/path/to/tinkerloop/src python -m tinkerloop.cli \
  --adapter /path/to/target/adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/target/scenarios \
  --tag <tag>
```

Rerun prior failures:

```bash
PYTHONPATH=/path/to/tinkerloop/src python -m tinkerloop.cli \
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
