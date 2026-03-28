# Copilot Instructions

## Project Shape

Tinkerloop is a small eval-driven harness. Keep the core generic and keep target-specific logic in target repos.

## Always Read First

- `README.md`
- `docs/STABILITY.md`
- `docs/TARGET_CONTRACT.md`
- `docs/WORKING_AGREEMENT.md`
- the matching local skill under `.codex/skills/`

## Skill Map

- Use `tinkerloop-runner` for execution, reruns, and artifact triage.
- Use `tinkerloop-integration` for target adapters, wrapper scripts, and target-owned setup.
- Use `tinkerloop-scenarios` for scenario JSON and deterministic checks.
- Use `pre-pr-review` for diff-scoped review passes.
  - Keep reviews findings-first.
  - Focus on bugs, regressions, stale tests, duplicated logic, and doc/code drift.
  - In review mode, do not edit code unless the user explicitly asks for fixes.

## Working Rules

- Keep changes narrow and bounded.
- Prefer deterministic checks before broader model-judged behavior.
- Keep report schema and CLI behavior aligned with docs.
- Do not move target-specific behavior into the Tinkerloop core.
- When a change affects the target repo contract, update the docs that describe the contract.
- When packaging, install, or CLI behavior changes, verify the installed-wheel path when practical.

## Implementation Style

- Read the relevant skill before editing.
- Use `rg` and `rg --files` for discovery.
- Prefer `apply_patch` for edits.
- Add or update tests with behavior changes.
- Verify the smallest meaningful slice first.
