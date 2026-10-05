"""List Gemini models this API key can call, so we use exact model IDs in .env."""

import json
import urllib.request

from qp_api.config import settings

if settings.google_api_key is None:
    raise SystemExit("GOOGLE_API_KEY is missing from .env")
request = urllib.request.Request(
    "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
    headers={"x-goog-api-key": settings.google_api_key.get_secret_value()},
)
with urllib.request.urlopen(request) as response:
    models = json.load(response)["models"]
print(f"{'MODEL ID (use this in .env)':<40} DISPLAY NAME")
for m in models:
    model_id = m["name"].removeprefix("models/")
    if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in model_id:
        print(f"{model_id:<40} {m.get('displayName', '')}")
