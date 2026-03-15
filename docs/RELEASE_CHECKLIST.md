# Release Checklist

This checklist is for a private release-prep flow today and a public `alpha`
release later.

## Contract And Docs

- confirm `README.md` matches current behavior
- confirm `docs/STABILITY.md` still matches the supported `v0.x` surface
- confirm `docs/TRUST_MODEL.md` still matches actual check/report behavior
- update `CHANGELOG.md`

## Validation

- run `python -m pytest -q`
- run `python -m build --wheel`
- install the wheel into a clean Python `3.12` environment
- run the starter target example through `examples/starter_target/adapter.py:create_adapter`
- run the demo app example through `examples/demo_app/adapter.py:create_adapter`

## Release Artifact

- verify the wheel name matches the intended version
- verify `tinkerloop --version`
- verify the release notes describe the project as `alpha`, not `beta`
- verify no release note implies benchmark or production-assurance claims

## Repo Hygiene

- confirm `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` exist
- confirm CI is green
- confirm issue and PR templates are present
