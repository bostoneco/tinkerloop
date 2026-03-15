---
name: tinkerloop-scenarios
description: Create or edit Tinkerloop scenario files and deterministic checks. Use when authoring scenario JSON, tagging slices, marking destructive flows, or confirming which check types the engine supports today.
---

# Tinkerloop Scenarios

Use this skill when writing or tightening scenario coverage.

Start with:
- `examples/demo_app/scenarios/`
- `src/tinkerloop/engine.py`
- `docs/WORKING_AGREEMENT.md`

## Current scenario shape

Each file is JSON with:
- `scenario_id`
- `description`
- `tags`
- `destructive`
- `turns[]`

Each turn has:
- `user`
- `checks[]`

## Supported check types

Read `src/tinkerloop/engine.py` if you need to confirm behavior.
Current checks are:
- `assistant_contains_all`
- `assistant_contains_any`
- `assistant_not_contains`
- `tool_used`
- `tool_call_count_at_most`
- `tool_call_matches`

## Authoring rules

- Keep one scenario focused on one behavior family.
- Add tags so reruns can stay narrow.
- Mark destructive flows explicitly and keep them opt-in.
- Prefer deterministic checks over vague phrasing checks.
- When tool path matters, assert it with `tool_used` or `tool_call_matches`.
- Avoid brittle wording unless exact phrasing is the real product requirement.

## Minimal pattern

```json
{
  "scenario_id": "cleanup_preview_first_unit",
  "description": "Preview one cleanup unit before execution.",
  "tags": ["cleanup", "preview"],
  "turns": [
    {
      "user": "Preview the first cleanup unit",
      "checks": [
        {"type": "assistant_contains_all", "values": ["Preview", "Undo"]},
        {"type": "tool_call_matches", "tool": "cleanup", "arguments": {"dry_run": true}}
      ]
    }
  ]
}
```

## Validation flow

After editing scenarios, run the smallest slice that proves the change:

```bash
tinkerloop run \
  --adapter <adapter-factory> \
  --user-id <user-id> \
  --scenarios <scenario-dir> \
  --scenario <scenario-id>
```

Then inspect `latest.json`, `latest-failures.json`, and `latest-diagnosis.json`.
