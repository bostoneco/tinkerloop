# Contributing

## Who can contribute

Pull requests are accepted only from **maintainers and invited contributors**. If you are not yet an invited contributor:

- **Bug reports and feature ideas:** please open an [issue](https://github.com/bostoneco/tinkerloop/issues).
- **Code changes:** open an issue first to discuss; the maintainers may invite you to contribute via PR.

This keeps the contributor set limited and review manageable while the project is in alpha.

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

Tinkerloop supports **Python 3.10+**. This repo pins **Python 3.12.9** in [`.python-version`](.python-version) for local development. With `pyenv` installed:

```bash
pyenv local 3.12.9
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Change Standard

- Keep patches bounded to one concern.
- Add or update tests when behavior changes.
- Update docs when CLI behavior, contract behavior, or report artifacts change.
- Preserve schema version discipline for report artifacts.

## Pull Requests (invited contributors)

Before opening a PR:

- run `pytest -q`
- run `python -m build`
- verify the starter target quickstart still works
- describe user-facing behavior changes and any stable-surface impact

## Release Policy

Releases are cut by the maintainers. See [CHANGELOG.md](CHANGELOG.md) for version history.
