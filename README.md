<p align="center">
  <img src="https://raw.githubusercontent.com/bostoneco/tinkerloop/main/docs/assets/tinkerloop-logo.png" alt="Tinkerloop" width="200">
</p>

# Tinkerloop

AI agents fail in ways unit tests can't catch — wrong tool calls, hallucinated answers, broken multi-turn flows. Tinkerloop is a scenario-based testing harness that replays conversations against your agent, runs deterministic checks on every response and tool call, and gives you a clear diagnosis when something breaks.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![PyPI](https://img.shields.io/pypi/v/tinkerloop-ai)](https://pypi.org/project/tinkerloop-ai/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Why Tinkerloop

- **Deterministic checks, not LLM-as-judge.** Every check is reproducible, fast, and free. No flaky evals, no paying for a judge model.
- **Assert on tool calls, not just text.** Verify your agent called the right tools with the right arguments — not just that the final response looks plausible.
- **Two-stage run / confirm.** Fast repair loops iterate on failures quickly; a separate confirmation loop validates against the real agent before you trust the result.
- **CI-gatable by design.** Exit codes distinguish "repair passed" (code 3) from "confirmed green" (code 0) so your pipeline can enforce the difference.
- **Architecture-agnostic.** Works with LangGraph, MCP tool servers, custom orchestrators, or any app that exposes a callable or command entrypoint. The target app doesn't need to be Python.
- **Built for coding agents.** Point Codex, Claude Code, Copilot, or Cursor at the installed package or the repo and the agent picks up the CLI, diagnosis artifacts, and repair loop without additional setup. The outer coding model reads the diagnosis, patches your agent, and reruns — that's the intended workflow.

## How It Works

```
write scenario → tinkerloop run → diagnose → patch → rerun → tinkerloop confirm
```

1. Write a JSON scenario with user turns and deterministic checks
2. `tinkerloop run` replays the conversation through your agent's adapter
3. Tinkerloop evaluates every check and writes a diagnosis artifact
4. Fix the target code using the diagnosis
5. Rerun failed scenarios until they pass
6. `tinkerloop confirm` validates against the real agent before the result is final

## Example

A scenario that tests whether a RAG agent looks up the right document and answers correctly:

```json
{
  "scenario_id": "lookup_refund_policy",
  "description": "Agent should search the knowledge base and cite the refund window",
  "tags": ["rag", "policy"],
  "turns": [
    {
      "user": "What is your refund policy?",
      "checks": [
        { "type": "tool_used", "values": ["search_knowledge_base"] },
        { "type": "assistant_contains_all", "values": ["30 days", "full refund"] },
        { "type": "assistant_not_contains", "values": ["I don't know", "I'm not sure"] }
      ]
    }
  ]
}
```

Run it:

```bash
tinkerloop run \
  --adapter your_project/tinkerloop_adapter.py:create_adapter \
  --user-id test-user \
  --scenarios scenarios/
```

When a check fails, Tinkerloop tells you exactly what went wrong:

```
Scenarios: 1, passed: 0, failed: 1
- [FAIL] lookup_refund_policy: Agent should search the knowledge base and cite the refund window
  turn 1: missing tools: ['search_knowledge_base']
          missing substrings: ['30 days']
```

The diagnosis artifact (`latest-diagnosis.json`) gives structured evidence for automated or manual triage:

```json
{
  "summary": {
    "failed_scenario_count": 1,
    "failed_scenario_ids": ["lookup_refund_policy"]
  },
  "diagnosis_items": [
    {
      "scenario_id": "lookup_refund_policy",
      "primary_symptoms": [
        "missing tools: ['search_knowledge_base']",
        "missing substrings: ['30 days']"
      ]
    }
  ]
}
```

Fix the agent and rerun. A green repair loop exits with code `3` — that
means repair passed but the loop is not complete. Run `tinkerloop confirm`
to finish:

```bash
tinkerloop run --adapter ... --scenarios scenarios/ --failed-from artifacts/reports

tinkerloop confirm --adapter ... --scenarios scenarios/ --non-interactive
```

## Quick Start

Install from PyPI:

```bash
pip install tinkerloop-ai
```

Create an adapter in your target repo:

```python
from tinkerloop.adapters import PythonAppAdapter

def create_adapter() -> PythonAppAdapter:
    return PythonAppAdapter(
        handler_path="your_app.agent:handle_message",
        patch_targets=["your_app.tools:execute_tool"],
    )
```

If your app uses a runner command, use `CommandAppAdapter`. For apps that need full control over trace capture, subclass `AppAdapter` directly. See the [Adapter Guide](docs/ADAPTER_GUIDE.md).

Add a scenario JSON file (see [Example](#example) above), then run:

```bash
tinkerloop run \
  --adapter your_project/tinkerloop_adapter.py:create_adapter \
  --user-id test-user \
  --scenarios scenarios/
```

When the repair loop passes (exit code 3), confirm against the real agent:

```bash
tinkerloop confirm \
  --adapter your_project/tinkerloop_adapter.py:create_adapter \
  --user-id test-user \
  --scenarios scenarios/ \
  --non-interactive
```

`--adapter` accepts an import path (`your_project.adapter:create_adapter`) or a file path (`/path/to/adapter.py:create_adapter`).

### From Source

```bash
git clone https://github.com/bostoneco/tinkerloop.git
cd tinkerloop
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
tinkerloop run \
  --adapter examples/starter_target/adapter.py:create_adapter \
  --user-id demo-user \
  --scenarios examples/starter_target/scenarios
```

## What You Can Check

| Check type | What it asserts | Scenario JSON |
|---|---|---|
| `assistant_contains_all` | Response includes every substring | `"values": ["30 days", "full refund"]` |
| `assistant_contains_any` | Response includes at least one | `"values": ["approved", "confirmed"]` |
| `assistant_not_contains` | Response includes none of these | `"values": ["I don't know"]` |
| `tool_used` | Agent called the named tool | `"values": ["search_knowledge_base"]` |
| `tool_call_count_at_most` | Tool was called at most N times | `"tool": "send_email", "max": 1` |
| `tool_call_matches` | Tool was called with specific arguments | `"tool": "send_email", "arguments": {"confirmed": true}` |

Checks are intentionally narrow and deterministic. If a behavior matters, encode it as an explicit check rather than relying on a broad pass/fail signal.

## Multi-Turn and Destructive Scenarios

Scenarios can span multiple turns and assert on each one independently. Mark destructive scenarios so they can be gated or isolated:

```json
{
  "scenario_id": "send_email_with_confirmation",
  "description": "Agent should compose, confirm, then send — checking tool args at each step",
  "destructive": true,
  "tags": ["email", "guardrail"],
  "turns": [
    {
      "user": "Send a test email to alice@example.com",
      "checks": [
        { "type": "tool_used", "values": ["compose"] },
        { "type": "assistant_contains_all", "values": ["Confirm to send"] }
      ]
    },
    {
      "user": "send",
      "checks": [
        { "type": "tool_call_matches", "tool": "compose", "arguments": { "confirmed": true } },
        { "type": "assistant_contains_all", "values": ["Email sent"] }
      ]
    }
  ]
}
```

Run a tagged slice:

```bash
tinkerloop run --adapter ... --scenarios scenarios/ --tag email --tag guardrail
```

## Tested Against Real Agents

Tinkerloop has been validated against multiple production agent architectures:

- A **multi-turn conversational email agent** with 25+ scenarios covering destructive flows, guardrails, undo operations, and tool argument assertions via `CommandAppAdapter`
- An **enterprise investigation agent** built on LangGraph with live API integrations, a custom `AppAdapter` subclass, and dynamic tool trace capture

These integrations exercise different adapter shapes, check types, and orchestrator complexities across the full contract surface.

## Artifacts

Each run writes structured JSON artifacts for tooling and CI integration:

| Artifact | Purpose |
|---|---|
| `latest.json` | Full report for the most recent run |
| `latest-failures.json` | Failed scenarios only |
| `latest-diagnosis.json` | Structured diagnosis with symptoms and confirmation status |
| `confirm-latest.json` | Full report for the most recent confirmation run |
| `confirm-latest-failures.json` | Failed confirmation scenarios |
| `confirm-latest-diagnosis.json` | Confirmation diagnosis |

Repair and confirmation artifacts are kept separate. A green repair loop is not a final pass — `confirmation_status` in the diagnosis artifact tracks whether the result has been confirmed against the real agent.

## Docs

- [Project Charter](docs/PROJECT_CHARTER.md) — goal, primary use case, non-goals
- [Architecture](docs/ARCHITECTURE.md) — engine, adapter, scenarios, hard boundaries
- [Quickstart: Target Repo](docs/QUICKSTART_TARGET_REPO.md) — minimal integration path
- [Adapter Guide](docs/ADAPTER_GUIDE.md) — `PythonAppAdapter` vs `CommandAppAdapter` vs `AppAdapter`
- [Target Contract](docs/TARGET_CONTRACT.md) — public integration boundary
- [Orchestrator Model](docs/ORCHESTRATOR_MODEL.md) — inner target orchestrator vs outer coding model
- [Trust Model](docs/TRUST_MODEL.md) — what pass/fail results mean and don't mean
- [Working Agreement](docs/WORKING_AGREEMENT.md) — day-to-day workflow and run discipline
- [Worked Example](docs/WORKED_EXAMPLE.md) — failure → diagnosis → rerun walkthrough
- [Troubleshooting](docs/TROUBLESHOOTING.md) — first-run failure modes
- [Stability](docs/STABILITY.md) — supported `v0.x` surface and experimental boundaries

## Status

Tinkerloop is in **alpha** (`v0.1.x`). The CLI commands, adapter interfaces, check types, and report schemas documented above are the supported contract for `v0.x`. See [STABILITY.md](docs/STABILITY.md) for the full stability boundary.

The project is designed for teams that can own a target adapter and scenario library. It is not a zero-config framework or a general benchmark suite.

## License

Apache License 2.0 — use, modify, and distribute freely; includes a patent grant. See [LICENSE](LICENSE).

## Contributing

PRs are accepted from maintainers and invited contributors. For bugs or ideas, open an [issue](https://github.com/bostoneco/tinkerloop/issues). See [CONTRIBUTING.md](CONTRIBUTING.md).
