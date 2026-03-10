from __future__ import annotations

import json
from typing import Any


def execute_tool(
    tool_name: str,
    user_id: str,
    arguments: dict[str, Any] | None,
    correlation_id: str | None = None,
) -> str:
    payload = {
        "status": "ok",
        "tool_name": tool_name,
        "user_id": user_id,
        "arguments": dict(arguments or {}),
        "correlation_id": correlation_id,
    }
    if tool_name == "cleanup":
        payload["user_safe_summary"] = "Prepared a cleanup preview."
        return json.dumps(payload)
    if tool_name == "undo":
        payload["user_safe_summary"] = "Reverted the last cleanup action."
        return json.dumps(payload)
    payload["status"] = "error"
    payload["user_safe_summary"] = "Unknown tool."
    return json.dumps(payload)


def handle_user_message(*, user_id: str, user_text: str, correlation_id: str) -> str:
    lowered = user_text.lower()
    if "undo" in lowered:
        execute_tool("undo", user_id, {"action": "cleanup"}, correlation_id=correlation_id)
        return "Undid the last cleanup action."
    if "preview" in lowered:
        execute_tool(
            "cleanup",
            user_id,
            {"dry_run": True, "limit": 1, "scope": "first_unit"},
            correlation_id=correlation_id,
        )
        return "Preview ready for the first cleanup unit. Undo will be available after execution."
    execute_tool(
        "cleanup",
        user_id,
        {"dry_run": False, "limit": 1, "scope": "first_unit"},
        correlation_id=correlation_id,
    )
    return "Executed the first cleanup unit. Undo is available."
