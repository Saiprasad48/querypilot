"""Call POST /api/ask and print each SSE event as it arrives.

Usage:
    uv run python scripts/stream_client.py "question" [thread_id]
Set QP_API_URL to target a deployed API (defaults to the local server).
"""

import json
import os
import sys
import time

import httpx

API_URL = os.getenv("QP_API_URL", "http://127.0.0.1:8000").rstrip("/")
question = sys.argv[1]
thread_id = sys.argv[2] if len(sys.argv) > 2 else None

print(f"Calling {API_URL}/api/ask")
started = time.perf_counter()

with httpx.stream(
    "POST",
    f"{API_URL}/api/ask",
    json={"question": question, "thread_id": thread_id},
    timeout=120,
) as response:
    if response.status_code != 200:
        response.read()
        print(f"HTTP {response.status_code}: {response.text}")
        sys.exit(1)
    event = ""
    for line in response.iter_lines():
        if line.startswith("event: "):
            event = line.removeprefix("event: ")
        elif line.startswith("data: "):
            data = json.loads(line.removeprefix("data: "))
            t = f"{time.perf_counter() - started:5.1f}s"
            if event == "step":
                print(f"{t}  step   {data['node']:<10} {data['ms']} ms")
            elif event == "rows":
                print(f"{t}  rows   {data['row_count']} rows, columns {data['columns']}")
            elif event == "answer":
                print(f"{t}  answer {data['answer'].get('summary')}")
            elif event == "usage":
                print(f"{t}  usage  in={data['input_tokens']} out={data['output_tokens']}")
            else:
                print(f"{t}  {event:<6} {data}")
