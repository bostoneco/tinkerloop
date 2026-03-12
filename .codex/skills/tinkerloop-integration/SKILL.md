---
name: tinkerloop-integration
description: Add Tinkerloop to a target project or update a target-owned integration. Use when creating or editing adapters, wrapper scripts, or target-owned scenario directories, especially when the target repo lives outside the Tinkerloop repo.
---

# Tinkerloop Integration

Use this skill when a project needs to be retrofitted for Tinkerloop or when an existing target-owned integration needs to be cleaned up.

Start with:
- `docs/TARGET_CONTRACT.md`
- `examples/demo_app/adapter.py`
- `src/tinkerloop/adapters/base.py`

## Default shape

Keep Tinkerloop integration in the target repo:

```text
target-repo/
  tinkerloop_<project>/
    adapter.py
    scenarios/
  scripts/
    run_tinkerloop.py
```

Tinkerloop itself stays generic.

## Choose the adapter

- Use `PythonAppAdapter` when the target exposes a Python callable entrypoint and you can patch the real tool execution path.
- Use `CommandAppAdapter` when the target is another stack, already has a runner script, or needs an explicit subprocess boundary.

## Required integration surface

Every integration needs:
- `create_adapter()`
- target-owned scenarios
- a real user entrypoint
- real tool trace capture

Add these adapter methods when the target needs them:
- `preflight()`
- `runtime_spec()`
- `runtime_candidates()`
- `select_runtime()`
- `run_metadata()`

## Portable run shape

Do not assume the target repo sits next to Tinkerloop.
Prefer explicit adapter and scenario paths:

```bash
PYTHONPATH=/path/to/tinkerloop/src python -m tinkerloop.cli \
  --adapter /path/to/target-repo/tinkerloop_project/adapter.py:create_adapter \
  --user-id <user-id> \
  --scenarios /path/to/target-repo/tinkerloop_project/scenarios
```

If the target repo wants a friendlier command, add a wrapper script in the target repo that resolves the Tinkerloop location through `TINKERLOOP_REPO` or a local install.

## Integration rules

- Keep auth checks, env names, business rules, deploy logic, and scenarios in the target repo.
- Resolve runtime from the target repo boundary, not from machine-wide guesses.
- Trace the real execution path; do not fake tool traces in the adapter.
- Use the smallest working scaffold first, then add more scenarios.
