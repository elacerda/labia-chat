"""Tests for Server-Sent Events formatting helpers."""

import pytest

from labia_chat.api.sse import sse_json_event, sse_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello", "data: hello\n\n"),
        ("\n", "data: \ndata: \n\n"),
        ("\n\n", "data: \ndata: \ndata: \n\n"),
        ("hello\n", "data: hello\ndata: \n\n"),
        ("```python\n", "data: ```python\ndata: \n\n"),
        ("", ""),
    ],
)
def test_sse_text_preserves_newlines_and_empty_chunks(text: str, expected: str):
    assert sse_text(text) == expected


def test_sse_json_event_formats_control_event_without_extra_spaces():
    assert (
        sse_json_event({"message_id": "msg-123"}, event="done")
        == 'event: done\ndata: {"message_id":"msg-123"}\n\n'
    )
