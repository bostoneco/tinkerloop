# Contributing

Contributions are welcome. This guide describes the project’s contribution standard.

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

Use **Python 3.12** (e.g. `python3.12 -m venv .venv`, then activate and):

```bash
pip install -e .[dev]
pytest -q
```

## Change Standard

- Keep patches bounded to one concern.
- Add or update tests when behavior changes.
- Update docs when CLI behavior, contract behavior, or report artifacts change.
- Preserve schema version discipline for report artifacts.

## Pull Requests

Before opening a PR:

- run `pytest -q`
- run `python -m build --wheel`
- verify the starter target quickstart still works
- describe user-facing behavior changes and any stable-surface impact

## Release Policy

Releases are cut by the maintainers. See [CHANGELOG.md](CHANGELOG.md) for version history.
