"""Send several questions quickly from one client ID to see the rate limit kick in."""
import httpx

for i in range(1, 8):
    response = httpx.post(
        "http://127.0.0.1:8000/api/ask",
        json={"question": "hello"},
        headers={"X-Client-Id": "hammer-test-client"},
        timeout=60,
    )
    print(
        f"request {i}: {response.status_code}  "
        f"remaining={response.headers.get('X-RateLimit-Remaining')}  "
        f"retry_after={response.headers.get('Retry-After')}"
    )