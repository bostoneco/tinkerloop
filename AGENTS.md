## Local Skills

This repo ships a small set of local Codex skills under `.codex/skills/`.
Use them when the task matches their workflow.

- `tinkerloop-integration`: retrofit another project for Tinkerloop, add or update a target-owned adapter, choose between `PythonAppAdapter` and `CommandAppAdapter`, or add a target-owned wrapper script. File: `.codex/skills/tinkerloop-integration/SKILL.md`
- `tinkerloop-scenarios`: create or edit scenario JSON, tighten deterministic checks, or verify the current supported check types. File: `.codex/skills/tinkerloop-scenarios/SKILL.md`
- `tinkerloop-runner`: run Tinkerloop, rerun failed scenarios, inspect artifacts, and follow the repo's narrow-first triage flow. File: `.codex/skills/tinkerloop-runner/SKILL.md`

## Usage Notes

- Read only the matching `SKILL.md` first.
- Prefer repo docs and example files referenced by the skill instead of loading unrelated files.
- Keep target-specific logic in the target repo, not in Tinkerloop.
