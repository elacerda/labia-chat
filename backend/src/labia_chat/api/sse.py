"""Helpers for formatting Server-Sent Events."""

import json
from typing import Any


def sse_text(text: str) -> str:
    """Format a plain text SSE data message."""
    if text == "":
        return ""

    safe_text = text.replace("\n", "\ndata: ")
    return f"data: {safe_text}\n\n"


def sse_json_event(obj: Any, event: str) -> str:
    """Format a structured SSE control event."""
    data = json.dumps(obj, separators=(",", ":"))
    safe_data = data.replace("\n", "\ndata: ")
    return f"event: {event}\ndata: {safe_data}\n\n"
