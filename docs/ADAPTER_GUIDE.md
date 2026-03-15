# Adapter Guide

Choose the narrowest adapter shape that exercises the real target behavior you
care about.

## Use `PythonAppAdapter` When

- the target exposes a Python callable entrypoint
- the target tool execution path can be patched in-process
- you want the fastest local loop with the least target-side scaffolding

Typical inputs:

- `handler_path`
- `patch_targets`
- optional `repo_root`
- optional `env_files`

## Use `CommandAppAdapter` When

- the target already has a runner command
- the target is not Python-native
- you need the target to own startup, environment, or process boundaries

Typical inputs:

- `command_builder`
- `workdir`
- optional `env_files`
- optional `env_overrides`

## Decision Rule

- prefer `PythonAppAdapter` for direct callable targets inside one repo
- prefer `CommandAppAdapter` when the target needs its own process boundary

## First-Run Checklist

- `preflight()` blocks clearly on missing auth/config/runtime
- runtime selection comes from the target repo boundary
- traces reflect the real tool path, not a fake wrapper path
- the adapter exposes enough `run_metadata()` to explain what was exercised
