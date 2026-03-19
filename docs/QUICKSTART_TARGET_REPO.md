# Quickstart: Target-Owned Integration

This is the shortest path from zero to a working target-owned integration.

## 1. Install Tinkerloop

Tinkerloop requires **Python 3.12+**. If you are working from a source checkout of this repo, use the pinned `3.12.9` from [`.python-version`](../.python-version).

From a wheel release:

```bash
python3.12 -m pip install /path/to/tinkerloop-<version>-py3-none-any.whl
```

For local development:

```bash
cd /path/to/tinkerloop
pyenv local 3.12.9
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Start From The Starter Target

Use [`examples/starter_target/`](../examples/starter_target/) as the minimum
reference shape:

- one target app callable
- one traced tool function
- one adapter factory
- one scenario file

## 3. Create A Target-Owned Adapter

Your target repo should expose one file such as:

```python
from tinkerloop.adapters import PythonAppAdapter


def create_adapter() -> PythonAppAdapter:
    return PythonAppAdapter(
        handler_path="your_project.app:handle_user_message",
        patch_targets=["your_project.app:execute_tool"],
    )
```

If your target needs a runner command instead, use `CommandAppAdapter`.

## 4. Add One Narrow Scenario

Create one JSON file with one behavior family and deterministic checks.
See [`examples/starter_target/scenarios/greet_user_by_name.json`](../examples/starter_target/scenarios/greet_user_by_name.json).

## 5. Run The Smallest Slice

```bash
tinkerloop \
  run \
  --adapter /path/to/target_adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios /path/to/scenarios
```

## 6. Inspect Artifacts

Treat these as primary evidence:

- `latest.json`
- `latest-failures.json`
- `latest-diagnosis.json`

## 7. Grow Carefully

- add tags before adding more scenarios
- keep destructive flows opt-in
- only widen scope after the narrow slice is stable
