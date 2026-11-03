"""Tiny disk cache for model calls made during evaluation (generator answers and judge replies).

The key is a hash of everything that could change the reply (model, settings, prompt text), so a
changed prompt or setting never reuses an old reply. Reruns of an unchanged run cost nothing, and a
run that crashes part-way (for example a Gemini 503) resumes where it stopped.
"""
import hashlib
import json

import config


def _path(key_parts):
    blob = json.dumps(key_parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return config.GEN_EVAL_CACHE_DIR / f"{hashlib.sha256(blob).hexdigest()[:24]}.json"


def cached(key_parts, compute, use_cache=True):
    """Return the stored value for key_parts, or call compute() and store its result."""
    path = _path(key_parts)
    if use_cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    value = compute()
    config.GEN_EVAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return value
