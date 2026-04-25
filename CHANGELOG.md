# Changelog

All notable changes to Tinkerloop should be recorded here.

## Unreleased

### Changed

- documentation steady-state pass: retired the roadmap-shaped planning docs (`docs/IMPLEMENTATION_PLAN.md`, `docs/MVP_PLAN.md`) and folded the still-load-bearing invariants and runtime-inspection rules into `docs/ARCHITECTURE.md` as a "Hard Boundaries" section
- clarified exit-code `3` and confirmation-required language across README, QUICKSTART, and the orchestrator-model doc so the repair-vs-confirm gate reads the same in every place a user encounters it
- renamed `docs/ACTOR_MODEL.md` to `docs/ORCHESTRATOR_MODEL.md` (and aligned dependent headings) to match the "inner target orchestrator / outer coding model" terminology already used in body content
- removed the duplicated "Security Direction" section from `docs/ARCHITECTURE.md`; `SECURITY.md` is the single canonical home for security posture and the long-term remote-driver direction
- added Project Charter, Architecture, and Working Agreement to the README docs list so the front-door catalog matches the actual doc set
- dropped the dated "Smoke Reproducibility Note" from `docs/TRUST_MODEL.md`; stale ground-truth in a trust doc trains readers to ignore freshness signals everywhere

## 0.1.7

### Changed

- switched the README logo to an absolute GitHub raw URL so the image can render on PyPI project pages

## 0.1.6

### Changed

- refined the public positioning around improving AI agents and rewrote the README around practical scenario-driven usage
- aligned the package docstring and PyPI-facing metadata with the current agent-improvement framing
- preserved richer confirmation status on repair runs, made timestamped reports collision-safe, and simplified CLI execution flow through shared engine helpers
- removed duplicate wheel-smoke workflow logic in favor of a shared smoke script used by CI and release publishing

## 0.1.5

### Changed

- `tinkerloop run` now exits with code `3` after a green repair loop so confirmation is a real gate for CI and coding models
- `tinkerloop confirm` now writes blocked confirmation artifacts with `confirmation_status: "blocked"` and the preflight error when infra prevents validation
- CLI summaries, diagnosis artifacts, smoke workflows, and user docs now reflect the confirmation gate instead of treating it as a soft suggestion

## 0.1.4

### Changed

- repair-loop runs now warn when confirmation is missing or stale instead of silently looking final
- diagnosis artifacts now expose `confirmation_status` so coding models can detect the gap directly
- green repair summaries now mark results as provisional until confirmation passes
- actor-model docs now treat missing or stale confirmation as a required follow-up

## 0.1.3

### Changed

- renamed the PyPI distribution to `tinkerloop-ai` and prepared Trusted Publishing for stable releases
- lowered the supported Python floor to `3.10` and expanded CI coverage to `3.10` through `3.12`
- added an explicit `confirm` command, confirmation artifact namespace, and actor-model docs for outer coding-model vs inner target-orchestrator workflows

## 0.1.2

### Changed

- hardened scenario execution failure handling so target failures and trace-capture failures are classified separately
- tightened scenario validation and removed duplicate CLI scenario execution paths
- expanded installed-wheel smoke coverage in CI and aligned docs with the current adapter and trust model contract
- refreshed the local pre-PR review skill and Copilot instructions to enforce findings-first review passes

## 0.1.1

### Changed

- refreshed the README opener to be more product-facing
