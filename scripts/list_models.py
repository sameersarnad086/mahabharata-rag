"""List the Gemini models this API key can use for text generation, to confirm the exact model id.

Usage: python scripts/list_models.py [filter-text]     e.g. python scripts/list_models.py flash
"""
import sys

from google import genai

needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
client = genai.Client()  # reads GEMINI_API_KEY
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions and needle in m.name.lower():
        print(m.name.replace("models/", ""), "|", getattr(m, "display_name", ""))
