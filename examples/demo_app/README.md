# Demo App

This is a tiny generic example target for Tinkerloop.

Run it with:

```bash
tinkerloop run \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios
```

This example exists only to demonstrate the public integration contract.
Real target apps should own their adapter, scenarios, and target-specific logic in their own repo.
