from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScenarioCheck:
    type: str
    values: list[str] = field(default_factory=list)
    value: str | int | float | bool | None = None
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    pattern: str | None = None
    max: int | None = None


@dataclass
class ScenarioTurn:
    user: str
    checks: list[ScenarioCheck] = field(default_factory=list)


@dataclass
class Scenario:
    scenario_id: str
    description: str
    turns: list[ScenarioTurn]
    destructive: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class ToolTrace:
    tool_name: str
    arguments: dict[str, Any]
    correlation_id: str | None
    duration_ms: int
    status: str | None
    user_safe_summary: str | None
    raw_result: dict[str, Any] | str


@dataclass
class CheckResult:
    check_type: str
    passed: bool
    detail: str


@dataclass
class TurnResult:
    user: str
    assistant: str
    tool_traces: list[ToolTrace]
    checks: list[CheckResult]
    passed: bool
    duration_ms: int


@dataclass
class ScenarioResult:
    scenario_id: str
    description: str
    destructive: bool
    user_id: str
    started_at: int
    duration_ms: int
    passed: bool
    turns: list[TurnResult]
