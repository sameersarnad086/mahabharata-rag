"""Generation: question + retrieved chunks -> a grounded, cited answer from a language model.

Library: google-genai (Google's official Python SDK). The key comes from the GEMINI_API_KEY
environment variable. Model, temperature and output limit are set in config.py.

Steps:
  1. build_prompt: instructions go in the system prompt; the numbered passages and the
     question go in the user message.
  2. generate_answer: one model call.
  3. check_citations: find the [n] markers in the answer and flag any that point to a passage
     number that was never provided (a made-up citation).
"""
import re
import time
from dataclasses import dataclass, field

import config

SYSTEM_PROMPT = """You answer questions about the Mahabharata (Kisari Mohan Ganguli's English translation).

Rules:
1. Use ONLY the numbered passages provided. Do not use outside knowledge, even if you know the answer.
2. After every claim, cite the passage number(s) in square brackets, like [2] or [1][3].
3. If the passages do not contain the answer, reply exactly: "The provided passages do not answer this question." You may add one sentence on what the passages do cover.
4. If passages disagree or give different names or numbers, report each version with its citation instead of choosing one.
5. One person can appear under several names. Treat two names as the same person only if a passage says so; otherwise keep them separate.
6. Be concise: a few sentences."""

CITATION = re.compile(r"\[(\d+)\]")


@dataclass
class Answer:
    text: str
    cited: list[int]                  # passage numbers the answer cites (valid ones)
    invalid_citations: list[int]      # cited numbers that do not exist in the prompt
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    model: str = ""
    user_message: str = field(default="", repr=False)


def build_prompt(question: str, hits: list) -> tuple[str, str]:
    """Return (system_prompt, user_message). `hits` are retrieval Hit objects, best first."""
    if hits:
        passages = "\n\n".join(f"[{h.rank}] ({h.citation})\n{h.text}" for h in hits)
    else:
        passages = "(no passages were retrieved)"
    return SYSTEM_PROMPT, f"Passages:\n\n{passages}\n\nQuestion: {question}"


def check_citations(answer_text: str, n_passages: int) -> tuple[list[int], list[int]]:
    """Return (valid cited numbers in order of first use, invalid cited numbers)."""
    valid, invalid = [], []
    for m in CITATION.finditer(answer_text):
        n = int(m.group(1))
        bucket = valid if 1 <= n <= n_passages else invalid
        if n not in bucket:
            bucket.append(n)
    return valid, invalid


RETRY_WAITS = (2, 4, 8, 16)   # seconds to wait before each retry of a temporary failure


def _call_with_retry(call):
    """Run call(); on a temporary Google-side error (429 rate limit, 5xx 'high demand') wait and retry."""
    from google.genai import errors
    for wait in (*RETRY_WAITS, None):
        try:
            return call()
        except errors.APIError as e:
            temporary = e.code == 429 or (isinstance(e.code, int) and e.code >= 500)
            if not temporary or wait is None:
                raise
            print(f"  (Gemini temporarily unavailable, code {e.code}; retrying in {wait}s)")
            time.sleep(wait)


def generate_answer(question: str, hits: list, client=None) -> Answer:
    from google import genai
    from google.genai import types

    system, user = build_prompt(question, hits)
    client = client or genai.Client()          # reads GEMINI_API_KEY from the environment
    response = _call_with_retry(lambda: client.models.generate_content(
        model=config.LLM_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=config.LLM_TEMPERATURE,
            max_output_tokens=config.LLM_MAX_OUTPUT_TOKENS,
        ),
    ))
    text = (response.text or "").strip()
    valid, invalid = check_citations(text, len(hits))
    usage = response.usage_metadata
    return Answer(
        text=text, cited=valid, invalid_citations=invalid, model=config.LLM_MODEL, user_message=user,
        prompt_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
    )
