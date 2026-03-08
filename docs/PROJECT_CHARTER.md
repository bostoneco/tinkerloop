# Project Charter

## Goal

Build a reusable open-source harness for exercising orchestrator-based apps in a scoped `test -> fix -> improve` loop.

## Primary Use Case

A target app already exists and exposes:
- a conversational entrypoint
- a tool or MCP execution surface
- enough runtime structure to trace tool activity

Tinkerloop should:
- replay realistic user scenarios
- capture the assistant reply and tool trajectory
- evaluate deterministic checks
- produce concrete failure artifacts for a developer to fix
- rerun the same scenarios after changes

## Non-Goals

- replace the target app's orchestrator
- become a general autonomous coding platform
- patch or deploy without a human decision point
- encode app-specific business logic in the core engine

## Product Shape

The core project should remain:
- adapter-driven
- scenario-driven
- report-driven
- easy to run locally against a target repository
