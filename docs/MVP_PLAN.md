# MVP Plan

## Phase T1: Core Harness

Required:
- scenario loader
- deterministic judge
- report writer
- CLI runner

Status:
- implemented

## Phase T2: Python Adapter

Required:
- configurable target callable import path
- optional env-file loading
- configurable patch points for tool tracing

Status:
- implemented

## Phase T3: Example Integration

Required:
- one real example app adapter
- one small scenario set
- documented quickstart

Status:
- implemented for Moppa example

## Phase T4: Developer Loop

Required:
- report-driven rerun workflow
- clear failure summaries
- artifact paths stable enough for automation

Status:
- implemented for stable reports and failed-scenario reruns

## Phase T5: Target Readiness And Runtime Fidelity

Required:
- adapter preflight before scenarios run
- repo-bounded inner-model resolution
- interactive candidate selection when runtime is ambiguous
- explicit overrides for provider/model

Status:
- partially implemented

## Phase T6: Improvement Loop

Required:
- structured handoff for outer developer agent
- optional judge extensions
- scenario tagging and scoped reruns

Status:
- not implemented
