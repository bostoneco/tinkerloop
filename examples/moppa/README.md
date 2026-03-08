# Moppa Example

This example shows how Tinkerloop can drive Moppa without keeping the harness inside the Moppa repository.

## Requirements

- the Moppa repo exists locally
- `TINKERLOOP_MOPPA_REPO` points to that repo if it is not the default sibling path
- Moppa environment variables are available, or Moppa's `.env` file is present

## Example

```bash
python -m tinkerloop.cli \
  --adapter examples.moppa.adapter:create_adapter \
  --user-id 5291202790 \
  --scenarios examples/moppa/scenarios
```
