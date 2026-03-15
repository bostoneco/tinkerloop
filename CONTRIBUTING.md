# Contributing

Tinkerloop is currently being prepared for its first public `alpha` release.
The repo remains private for now, but this guide is the contribution standard
that will ship with the project.

## Scope

Contributions should preserve the core project boundaries:

- keep Tinkerloop generic
- keep target-specific logic in target-owned adapters or example targets
- prefer deterministic checks before any model-judged behavior
- avoid automatic deploy or production-action surfaces

## Before You Start

1. Read [README.md](README.md), `docs/TARGET_CONTRACT.md`, and `docs/STABILITY.md`.
2. Confirm whether the change affects a stable `v0.x` surface or an experimental one.
3. For scenario work, keep the scope narrow and deterministic.

## Local Setup

```bash
python -m pip install -e .[dev]
python -m pytest -q
```

## Change Standard

- Keep patches bounded to one concern.
- Add or update tests when behavior changes.
- Update docs when CLI behavior, contract behavior, or report artifacts change.
- Preserve schema version discipline for report artifacts.

## Pull Requests

Before opening a PR:

- run `python -m pytest -q`
- run `python -m build --wheel`
- verify the starter target quickstart still works
- describe user-facing behavior changes and any stable-surface impact

## Release Policy

Until the project is public, contributions are by invitation.
This file is still maintained now so the public release can happen without a
separate docs scramble.
