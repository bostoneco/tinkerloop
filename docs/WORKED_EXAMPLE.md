# Worked Example: Failure To Rerun

This example shows the intended evidence trail:

1. run one narrow failing scenario
2. inspect `latest-diagnosis.json`
3. fix the target
4. rerun the failed set

## Example Failing Scenario

Use the starter target plus a scenario that expects the wrong name.
See [`examples/starter_target/failure_scenarios/greet_user_wrong_name.json`](../examples/starter_target/failure_scenarios/greet_user_wrong_name.json).

Run it:

```bash
tinkerloop \
  run \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/failure_scenarios
```

Observed result in private alpha-prep verification:

```text
Scenarios: 1, passed: 0, failed: 1
- [FAIL] starter_greet_user_wrong_name: Deliberately fail by expecting the wrong profile name.
  turn 1: missing substrings: ['Hello, Grace']
```

Key excerpt from `latest-diagnosis.json`:

```json
{
  "summary": {
    "failed_scenario_count": 1,
    "failed_scenario_ids": ["starter_greet_user_wrong_name"],
    "preflight_status": "ready",
    "selected_runtime": {
      "provider": "example",
      "model": "starter-target"
    }
  },
  "diagnosis_items": [
    {
      "scenario_id": "starter_greet_user_wrong_name",
      "primary_symptoms": ["missing substrings: ['Hello, Grace']"]
    }
  ]
}
```

Rerun only the failed set:

```bash
tinkerloop \
  run \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/failure_scenarios \
  --failed-from /path/to/report-dir
```

The corresponding diagnosis artifact records:

```json
{
  "scenario_ids": ["starter_greet_user_wrong_name"],
  "hint": "--failed-from <report-dir-or-report-file>"
}
```

This is not a benchmark.
It is a compact example of the intended debug loop.
