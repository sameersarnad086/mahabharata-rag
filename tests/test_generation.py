"""Checks for prompt building and citation checking (no model call). Run: python tests/test_generation.py"""
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.generation import build_prompt, check_citations


@dataclass
class H:
    rank: int
    citation: str
    text: str


def check(name, ok):
    print(("PASS" if ok else "FAIL"), name)
    return ok


hits = [H(1, "Section 10", "Alpha text"), H(2, "Section 20", "Beta text"), H(3, "Section 30", "Gamma text")]
system, user = build_prompt("Who is X?", hits)
results = [
    check("every passage appears, numbered, with its citation",
          all(f"[{h.rank}] ({h.citation})\n{h.text}" in user for h in hits)),
    check("passages are in rank order", user.index("Alpha") < user.index("Beta") < user.index("Gamma")),
    check("question comes last", user.rstrip().endswith("Question: Who is X?")),
    check("system prompt has the grounding and refusal rules",
          "ONLY the numbered passages" in system and "do not answer this question" in system),
    check("no hits -> prompt says nothing was retrieved", "(no passages were retrieved)" in build_prompt("Q", [])[1]),
    check("valid citations, first-use order", check_citations("A [2]. B [1][3]. C [2].", 3) == ([2, 1, 3], [])),
    check("made-up citation is flagged", check_citations("A [4]. B [1].", 3) == ([1], [4])),
    check("[0] is invalid", check_citations("A [0].", 3) == ([], [0])),
    check("no citations at all", check_citations("The provided passages do not answer this question.", 5) == ([], [])),
]
print(f"\n{sum(results)}/{len(results)} passed")

# --- retry on temporary Google-side errors (no network; sleeping is stubbed out) ---
import src.rag.generation as gen
from google.genai import errors

gen.time.sleep = lambda s: None
calls = {"n": 0}


def flaky(fail_times, code):
    calls["n"] = 0

    def call():
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise errors.APIError(code, {"error": {"message": "temporary"}})
        return "ok"
    return call


r2 = [
    check("503 twice, then success -> returns result after 3 calls",
          gen._call_with_retry(flaky(2, 503)) == "ok" and calls["n"] == 3),
    check("429 once, then success", gen._call_with_retry(flaky(1, 429)) == "ok" and calls["n"] == 2),
]
try:
    gen._call_with_retry(flaky(99, 503)); r2.append(check("503 forever -> raises after retries", False))
except errors.APIError:
    r2.append(check("503 forever -> raises after 5 attempts", calls["n"] == 5))
try:
    gen._call_with_retry(flaky(99, 400)); r2.append(check("400 is not retried", False))
except errors.APIError:
    r2.append(check("400 is not retried (1 attempt)", calls["n"] == 1))
print(f"\nretry checks: {sum(r2)}/{len(r2)} passed")
