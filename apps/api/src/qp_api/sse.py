"""Server Sent Events formatting: each event is 'event: <name>' + 'data: <json>' + blank line."""

import json
from typing import Any


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
