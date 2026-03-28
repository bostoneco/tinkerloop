# Adapter Guide

Choose the narrowest adapter shape that exercises the real target behavior you
care about.

## Use `PythonAppAdapter` When

- the target exposes a Python callable entrypoint
- the target tool execution path can be patched in-process through a standard callable
- you want the fastest local loop with the least target-side scaffolding

Typical inputs:

- `handler_path`
- `patch_targets`
- optional `repo_root`
- optional `env_files`

Current `v0.x` trace patching expects each `patch_targets` callable to use:

- `tool_name`
- `user_id`
- `arguments`
- optional `correlation_id=None`

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
- `run_metadata()` explains what repo root, env files, and runtime context were exercised

`AppAdapter.run_metadata()` is empty by default.
Real target adapters should override it with useful local execution context.
