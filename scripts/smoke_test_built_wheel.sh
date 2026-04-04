#!/usr/bin/env bash

set -euo pipefail

run_repair_loop_expect_gate() {
  set +e
  "$@"
  status=$?
  set -e
  if [ "$status" -ne 3 ]; then
    echo "Expected repair loop to exit 3 until confirmation passes, got $status" >&2
    exit 1
  fi
}

python -m venv /tmp/tinkerloop-smoke
source /tmp/tinkerloop-smoke/bin/activate
latest_wheel=$(ls -t dist/*.whl 2>/dev/null | head -n 1)
if [ -z "${latest_wheel:-}" ]; then
  echo "No built wheel found in dist/" >&2
  exit 1
fi
pip install "$latest_wheel"
tinkerloop --version

run_repair_loop_expect_gate tinkerloop run \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/scenarios \
  --report-dir /tmp/tinkerloop-starter-artifacts

tinkerloop confirm \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/scenarios \
  --report-dir /tmp/tinkerloop-starter-artifacts

run_repair_loop_expect_gate tinkerloop run \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --report-dir /tmp/tinkerloop-demo-artifacts

tinkerloop confirm \
  --adapter examples/demo_app/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/demo_app/scenarios \
  --report-dir /tmp/tinkerloop-demo-artifacts
