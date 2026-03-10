# Implementation Plan

This document is the handoff for continuing Tinkerloop development.
It captures the current state, hard design decisions, and the phased implementation plan.

## Project Summary

Tinkerloop is a reusable outer-loop harness for orchestrator-based apps.

It should:
- play the role of user
- exercise the target app through realistic multi-turn scenarios
- capture assistant replies and tool traces
- evaluate deterministic checks first
- generate actionable failure artifacts
- support a `test -> diagnose -> patch -> rerun` workflow

It should not:
- replace the target app orchestrator
- embed target-app business logic in the core engine
- guess across unrelated repositories or machine state
- deploy or patch production systems automatically

## Hard Boundaries

### 1. Core vs Adapter

Tinkerloop core must stay generic.

Core responsibilities:
- scenario loading
- turn execution orchestration
- deterministic checks
- result summarization
- report writing
- outer-loop workflow support

Adapter responsibilities:
- target-app preflight
- target-app runtime model resolution
- target-app trace patching
- target-app entrypoint invocation
- target-app specific setup and readiness checks

### 2. Target Repo Only

Tinkerloop must operate only on the targeted repo boundary.

Allowed sources for runtime inspection:
- target repo files
- target repo env/config files
- target repo code defaults
- target repo runtime endpoints or deployed config if the adapter explicitly defines them as part of the target system

Disallowed:
- scanning unrelated repos
- random machine-wide discovery
- guessing from other projects
- silent fallback based on global heuristics

### 3. Auth and External Setup Stay in the Target App

Example: Moppa requires Gmail connection.

Tinkerloop core must not know anything about Gmail auth.
That belongs in the Moppa adapter.

Correct behavior:
- adapter runs a preflight check
- if the target user is not connected, adapter returns a blocked status with a clear reason
- Tinkerloop stops cleanly and reports that the target app is not ready

### 4. Inner Model Fidelity

Tinkerloop should prefer to exercise the target app with the same inner orchestrator model the app is configured to use.

There are two model roles:
- inner model: used by the app under test
- outer model: used by Tinkerloop's future developer/analysis loop

The adapter must resolve the inner model from the target repo boundary.
The core should record it and surface it in reports.

If a single model cannot be resolved confidently:
- the adapter returns ranked candidates derived only from the target repo
- Tinkerloop presents those choices to the user
- non-interactive runs should fail unless an explicit override is provided

### 5. Future Secure Driver Contract

The long-term target-side integration must not become a production backdoor.

Future target-driver rules:
- target repos should expose a tiny fixed Tinkerloop contract rather than arbitrary code execution
- target-driver surfaces must be disabled in production
- preferred transports are infrastructure-authenticated and private, such as IAM-authenticated Lambda invoke
- no public anonymous test endpoints
- no arbitrary function dispatch
- no shell execution through the target app
- all test sessions must be auditable and kill-switchable

For AWS apps like Moppa, the preferred future shape is:
- non-prod only `TinkerloopDriverFunction`
- invoked through IAM, not public internet
- fixed operations only:
  - `preflight`
  - `start_session`
  - `send_turn`
  - `poll_events`
  - `get_trace`

This is a future implementation phase, not the current stopgap.

## Current Status

Implemented now:
- generic scenario model and deterministic checks
- generic report writer
- generic CLI runner
- `PythonAppAdapter`
- `CommandAppAdapter`
- tool trace recording through configurable patch targets
- Moppa example adapter
- Moppa example scenario set
- feedback-loop logic removed from Moppa and moved here

Current docs:
- `docs/PROJECT_CHARTER.md`
- `docs/ARCHITECTURE.md`
- `docs/MVP_PLAN.md`
- `docs/IMPLEMENTATION_PLAN.md`

Current example integration:
- `examples/moppa/adapter.py`
- `examples/moppa/scenarios/*.json`

## Current Gaps

Not implemented yet:
- outer developer loop with structured patch workflow
- judge expansion beyond deterministic checks
- target repo mutation workflow with explicit human gate
- secure target-driver contract and target manifest

## Current Moppa Stopgap

For Moppa urgency, the current stopgap path is intentionally simpler than the future secure driver.

Current stopgap:
- Tinkerloop launches a target-owned Moppa script from the Moppa repo
- Moppa's own orchestrator runs locally in Moppa's `.venv`
- Moppa tool execution is proxied to deployed `/mcp/tool` via `API_BASE_URL`
- local conversation/memory persistence is disabled in the runner to avoid DynamoDB/RDS coupling

Why this exists:
- it removes Telegram from the loop now
- it exercises Moppa's own orchestrator instead of replacing it
- it avoids waiting for the full secure target-driver implementation

Current limitations:
- it is for local/staging use only
- it does not provide the final secure non-prod driver architecture
- for Moppa today, the deployed `/mcp/tool` path may require a Moppa MCP-connected user id rather than a Telegram-only user id
- local-only stopgap mode does not have full access to deployed conversation history or stored scan-summary state unless Moppa later adds a secure target driver

## Phased Plan

## Phase T1: Core Harness

Goal:
- establish a generic runner and deterministic judge

Status:
- implemented

Required behavior:
- load scenario files
- run multi-turn scenarios
- capture assistant replies
- capture tool traces through adapter-provided tracing
- evaluate deterministic checks
- write JSON report artifacts

Acceptance:
- core unit tests green
- CLI can run a scenario set against a configured adapter

## Phase T2: Python Target Adapter

Goal:
- support Python-based target apps without embedding target logic in the core

Status:
- implemented

Required behavior:
- import a target callable from a configured import path
- load target env files if requested by the adapter
- patch configured tool execution points for trace collection

Acceptance:
- example adapter can call a target app entrypoint and collect tool traces

## Phase T3: Example Integration Ownership

Goal:
- move reusable harness logic out of target apps and keep only app logic inside target repos

Status:
- implemented for Moppa

Required behavior:
- Tinkerloop owns the harness
- Moppa owns only Moppa logic
- example adapter and scenarios live in Tinkerloop, not Moppa

Acceptance:
- Moppa has no feedback-loop engine/docs/scripts left
- Moppa still passes tests after extraction

## Phase T4: Adapter Preflight Contract

Goal:
- make target readiness explicit before a run starts

Status:
- implemented for the current adapter contract and Moppa example

Required behavior:
- add a generic adapter `preflight()` contract
- return structured statuses such as:
  - `ready`
  - `blocked_auth`
  - `blocked_config`
  - `blocked_runtime`
- surface a clear message and stop early when blocked

Moppa-specific implementation:
- verify target user exists in Moppa
- verify Gmail auth state from Moppa-owned logic/config
- do not teach Tinkerloop core about Gmail

Acceptance:
- running the Moppa example against an unconnected user fails cleanly before scenario execution
- report includes preflight result

## Phase T5: Runtime Model Resolution Contract

Goal:
- make the inner orchestrator model explicit and repo-bounded

Status:
- implemented for the current adapter contract and Moppa example

Required behavior:
- add generic adapter methods such as:
  - `runtime_spec()` for high-confidence resolution
  - `runtime_candidates()` when resolution is missing or ambiguous
- runtime resolution may inspect only the target repo boundary
- record provider/model/source/confidence in the run report

Moppa-specific implementation:
- resolve from Moppa repo env/config/defaults first
- optionally inspect Moppa deployed runtime only if defined as part of the Moppa adapter boundary
- never scan unrelated repos

Acceptance:
- report includes resolved inner model metadata when available
- ambiguous model state produces a bounded candidate list with reasons

## Phase T6: Interactive Choice / Non-Interactive Policy

Goal:
- handle missing or ambiguous inner model cleanly

Status:
- partially implemented

Required behavior:
- interactive mode: present ranked repo-derived candidates and let the user choose
- non-interactive mode: fail unless explicit override is supplied
- support explicit overrides like:
  - provider
  - model
  - allow/disallow fallback

Acceptance:
- user can select from a small candidate list when multiple inner models are plausible

## Phase T7: Stopgap Conversation Bridge

Goal:
- support the simplest current reverse-Tinkerloop flow for target apps that already have a local orchestrator entrypoint

Status:
- implemented for Moppa as a stopgap

Required behavior:
- add a generic subprocess command adapter
- allow target-owned runner scripts to emit trace files
- keep target-specific logic in the target repo or example adapter

Acceptance:
- Tinkerloop can run a target-owned command per user turn
- assistant reply is captured from stdout
- tool traces are captured from a sidecar trace file when provided

## Phase T8: Secure Target Driver Contract

Goal:
- replace stopgap repo-specific runners with a declared, secure target-driver contract

Status:
- not implemented

Required behavior:
- target repo declares a Tinkerloop contract explicitly
- target repo owns deploy, preflight, session, and trace operations
- target-driver surfaces are non-prod only and infrastructure-authenticated
- no public backdoor endpoints

Acceptance:
- a target repo can integrate with Tinkerloop without Tinkerloop embedding repo-specific transport logic
- driver contract is auditable and safe by default
- CI/non-interactive usage fails closed without explicit selection

## Phase T7: Failure Artifact Model

Goal:
- make failures easy for a developer or outer model to act on

Status:
- implemented for stable JSON report artifacts and failed-scenario extraction

Required behavior:
- stable artifact schema for:
  - scenario metadata
  - turn transcript
  - tool traces
  - failing checks
  - runtime metadata
  - preflight state
- stable artifact paths for reruns and automation

Implemented now:
- timestamped report files
- stable `latest.json`
- stable `latest-failures.json`
- failed-scenario ids recorded in report summaries
- failed-scenario ids loadable from a prior report file or report directory

Still missing:
- richer diagnosis payload tailored for outer developer-agent handoff

Acceptance:
- a failing run produces stable artifacts with enough structure for reruns and automation

## Phase T8: Outer Developer Loop

Goal:
- support the developer side of `test -> diagnose -> patch -> rerun`

Status:
- partially implemented

Required behavior:
- select failed scenarios only
- summarize failures into a compact diagnosis payload
- support repo patch/apply workflow against the target repo
- rerun only affected scenarios first, then full regression set
- always keep a human gate before pushing or deploying

Implemented now:
- failed-scenario reruns from prior reports
- compact diagnosis artifact for failed scenarios
- tag-based scoped runs for limited feature slices

Still missing:
- target-repo patch/apply workflow
- explicit human approval flow for mutations
- regression sequencing beyond manual reruns

Deferred follow-on ideas inspired by `karpathy/autoresearch`:
- add a target-local operator policy file such as `program.md` so the outer loop can follow app-specific diagnosis and improvement rules without hardcoding them into Tinkerloop core
- add a cross-run experiment ledger that records baseline, candidate, pass-rate delta, tool-usage delta, and keep/discard outcome for each attempted improvement
- add fixed-budget candidate evaluation so prompt, routing, config, or future patch experiments are compared on the same scoped scenario slice instead of open-ended retries
- upgrade diagnosis artifacts from symptom-only summaries to hypothesis-oriented handoff items with likely cause, suggested next experiment, and confidence
- if target-repo mutation is added later, keep the writable surface explicit and bounded through an allowed-files manifest rather than free-form autonomous edits

Important constraint:
- this phase mutates the target repo, not the Tinkerloop repo
- mutation must be explicit, auditable, and bounded to the target repo under test

Acceptance:
- a developer can run a scoped improvement loop against one failing scenario family

## Phase T9: Judge Expansion

Goal:
- allow richer evaluations without making the core opaque

Status:
- not implemented

Required behavior:
- deterministic checks remain first-line gates
- optional LLM judge sits behind explicit configuration
- LLM-judge results must be recorded separately from deterministic checks
- no hidden pass/fail logic

Acceptance:
- deterministic-only runs remain supported
- LLM-judge runs clearly show what was model-judged vs deterministic

## Phase T10: Additional Adapters

Goal:
- prove Tinkerloop is reusable beyond Moppa

Status:
- not implemented

Candidate targets:
- another orchestrator + MCP app in the same org
- a non-MCP orchestrator app with a Python entrypoint
- later, a network/API adapter if needed

Acceptance:
- second target integration works without changing the Tinkerloop core model

## Immediate Next Work

The next implementation order should be:
1. adapter preflight contract
2. adapter runtime model resolution
3. candidate selection flow for ambiguous runtime models
4. failure artifact stabilization
5. outer developer loop for scoped reruns and repo patch workflow

This order matters because:
- preflight and runtime resolution are foundational for faithful runs
- artifact quality is needed before patch automation
- outer-loop mutation should not be built on top of weak run metadata

## Moppa-Specific Notes

Moppa remains the first example integration, but Moppa-specific logic must stay in the Moppa adapter.

That includes:
- Gmail auth readiness
- target user connection requirements
- inner model resolution from Moppa config
- Moppa-specific trace patch targets
- Moppa-specific scenario library

Tinkerloop core must not contain:
- Gmail logic
- Telegram logic
- Moppa business rules
- hardcoded Moppa config names outside the Moppa example adapter

## Acceptance Standard For Any Future Change

Every future phase should preserve these invariants:
- core stays generic
- target-specific logic stays in adapters/examples
- target repo only
- no silent model guessing
- no automatic production actions
- deterministic checks remain the first gate
