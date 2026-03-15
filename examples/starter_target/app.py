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
    if tool_name == "lookup_profile":
        payload["user_safe_summary"] = "Loaded the starter profile."
        payload["profile"] = {"name": "Ada"}
        return json.dumps(payload)
    payload["status"] = "error"
    payload["user_safe_summary"] = "Unknown tool."
    return json.dumps(payload)


def handle_user_message(*, user_id: str, user_text: str, correlation_id: str) -> str:
    lowered = user_text.lower()
    if "name" in lowered or "hello" in lowered:
        execute_tool(
            "lookup_profile",
            user_id,
            {"name": "Ada"},
            correlation_id=correlation_id,
        )
        return "Hello, Ada. Your starter target is wired up correctly."
    return "Ask me to say hello by name."
