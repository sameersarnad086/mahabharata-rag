"""The judge: a second model that grades answers, one narrow job per call.

Library: google-genai, the same SDK as the generator. Model and settings are in config.py.
Every call asks for JSON back (response_mime_type), and the reply is checked before use.

Jobs (each is a separate call that sees only the material that job needs):
  correctness    question + expected answer + answer          -> 1 / 0.5 / 0   (no passages shown)
  extract_claims the answer alone                             -> list of single factual claims
  verify_claims  the passages + the claims                    -> supported or not, per claim
  citations      (sentence, cited passages) pairs             -> backed or not, per pair
  relevance      question + answer                            -> addresses the question or not

`Judge` takes an `ask(system, user) -> {"reply": dict, "usage": dict}` function, so tests can
plug in a fake and run with no network.
"""
import json
from collections import Counter

import config
from src.rag import evalcache


class JudgeError(Exception):
    """The judge returned something we could not use."""


PREFACE = (
    "You are a strict, impartial grader for a question-answering system about the Mahabharata "
    "(Kisari Mohan Ganguli's English translation). Use ONLY the material given in the message. "
    "Do not use anything you know from elsewhere, even if you are sure it is true. "
    "Reply with a single JSON object in exactly the format requested, and nothing else.\n\n"
)

NAMES_RULE = (
    "Names: one person often has several names, titles and epithets (for example Arjuna, Partha and Dhananjaya). "
    "Different spellings of the same name (transliteration variants such as Hidimba and Hidimva, or Yudhishthira and "
    "Yudhisthira) always match. Treat two different names as the same person ONLY when the passages themselves show it, for example a passage "
    "that says 'Vyasa, also called Dwaipayana', or a passage where 'the king' or 'the Rishi' is clearly the person "
    "being discussed. Do NOT use what you know about who is who from anywhere else. If the passages do not make the "
    "identity clear, the names do not match. Never merge two different people who merely share a name. Names are the "
    "only thing this rule relaxes; every other fact must still be stated or directly implied by the passages.\n"
)

CORRECTNESS_TASK = (
    "Grade whether the answer is correct, using the expected answer as the truth.\n"
    "Score 1 = states the key fact(s) of the expected answer and nothing in it contradicts the expected "
    "answer (extra detail is fine). Score 0.5 = states only part of what the expected answer requires, "
    "or is too vague to count as the key fact. Score 0 = wrong, contradicts the expected answer, or "
    "does not answer.\n"
    'Reply: {"score": 1 or 0.5 or 0, "reason": "<one sentence>"}'
)

CLAIMS_TASK = (
    "Break the answer into separate factual claims.\n"
    "Rules: one fact per claim; each claim must make sense on its own (replace 'she', 'they', 'it' with "
    "the name); remove [n] citation markers; skip statements about the passages themselves (for example "
    "'The provided passages do not answer this question'); never add anything the answer does not say.\n"
    'Reply: {"claims": ["<claim>", "<claim>"]}'
)

VERIFY_TASK = (
    "For each numbered claim, decide whether the passages state it or directly imply it.\n"
    "A claim that is true in the real world but is not stated or directly implied by the passages is "
    "NOT supported. Judge each claim on its own.\n"
    + NAMES_RULE +
    'Reply: {"verdicts": [{"claim_number": 1, "supported": true or false, "evidence": '
    '"<short quote from the passages, or empty>"}]}'
)

CITATION_TASK = (
    "Below are numbered pairs. Each pair has one sentence from an answer and the passage(s) that the "
    "sentence cites. Judge each pair on its own, using only the passage text inside that pair.\n"
    "A sentence is backed only if EVERYTHING it states is stated or directly implied by its cited "
    "passage(s). If any part is not in them, it is not backed.\n"
    + NAMES_RULE +
    'Reply: {"results": [{"pair": 1, "backed": true or false, "reason": "<one sentence>"}]}'
)

RELEVANCE_TASK = (
    "Decide whether the answer addresses what the question asks. Being right or wrong does not matter "
    "here. Relevant = it attempts to answer the question asked. Not relevant = off topic, or it answers "
    "a different question.\n"
    'Reply: {"relevant": true or false, "reason": "<one sentence>"}'
)


def make_google_ask(use_cache=True):
    """Build the real `ask` function that calls the judge model (with caching and retry)."""
    from google import genai
    from google.genai import types

    from src.rag.generation import _call_with_retry

    client = genai.Client()           # reads GEMINI_API_KEY from the environment
    extra = {}
    if config.JUDGE_THINKING_LEVEL:
        extra["thinking_config"] = types.ThinkingConfig(thinking_level=config.JUDGE_THINKING_LEVEL)

    def ask(system, user):
        def compute():
            for _ in range(2):        # one retry if the reply is not valid JSON
                response = _call_with_retry(lambda: client.models.generate_content(
                    model=config.JUDGE_MODEL,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=config.JUDGE_TEMPERATURE,
                        max_output_tokens=config.JUDGE_MAX_OUTPUT_TOKENS,
                        response_mime_type="application/json",
                        **extra,
                    ),
                ))
                try:
                    reply = json.loads((response.text or "").strip())
                except json.JSONDecodeError:
                    continue
                u = response.usage_metadata
                return {"reply": reply, "usage": {
                    "prompt": getattr(u, "prompt_token_count", None) or 0,
                    "output": getattr(u, "candidates_token_count", None) or 0,
                    "thinking": getattr(u, "thoughts_token_count", None) or 0}}
            raise JudgeError("judge did not return valid JSON twice in a row")

        return evalcache.cached(
            [config.JUDGE_MODEL, config.JUDGE_TEMPERATURE, config.JUDGE_THINKING_LEVEL, system, user],
            compute, use_cache)

    return ask


def passages_text(hits):
    return "\n\n".join(f"[{h.rank}] {h.text}" for h in hits)


class Judge:
    def __init__(self, ask):
        self.ask = ask
        self.calls = 0
        self.usage = Counter()

    def _run(self, task, user):
        res = self.ask(PREFACE + task, user)
        self.calls += 1
        for k, v in (res.get("usage") or {}).items():
            self.usage[k] += v or 0
        reply = res["reply"]
        if not isinstance(reply, dict):
            raise JudgeError(f"expected a JSON object, got {type(reply).__name__}")
        return reply

    def correctness(self, question, expected, answer):
        r = self._run(CORRECTNESS_TASK,
                      f"Question: {question}\n\nExpected answer (the truth): {expected}\n\nAnswer to grade: {answer}")
        score = r.get("score")
        if score not in (0, 0.5, 1):
            raise JudgeError(f"correctness score must be 0, 0.5 or 1, got {score!r}")
        return {"score": float(score), "reason": str(r.get("reason", ""))}

    def extract_claims(self, answer):
        r = self._run(CLAIMS_TASK, f"Answer:\n{answer}")
        claims = r.get("claims")
        if not isinstance(claims, list):
            raise JudgeError("claims must be a list")
        return [str(c).strip() for c in claims if str(c).strip()]

    def verify_claims(self, hits, claims):
        numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))
        r = self._run(VERIFY_TASK, f"Passages:\n\n{passages_text(hits)}\n\nClaims:\n{numbered}")
        by_no = {}
        for v in r.get("verdicts") or []:
            if isinstance(v, dict) and isinstance(v.get("supported"), bool):
                by_no[v.get("claim_number")] = v
        if sorted(by_no) != list(range(1, len(claims) + 1)):
            raise JudgeError("judge did not return exactly one verdict per claim")
        return [{"claim": claims[i - 1], "supported": by_no[i]["supported"],
                 "evidence": str(by_no[i].get("evidence", ""))} for i in range(1, len(claims) + 1)]

    def citations(self, pairs):
        """pairs: list of (sentence, passages_text). Returns one {'backed', 'reason'} per pair."""
        body = "\n\n".join(f"Pair {i}:\nSentence: {s}\nCited passage(s):\n{p}" for i, (s, p) in enumerate(pairs, 1))
        r = self._run(CITATION_TASK, body)
        by_no = {}
        for v in r.get("results") or []:
            if isinstance(v, dict) and isinstance(v.get("backed"), bool):
                by_no[v.get("pair")] = v
        if sorted(by_no) != list(range(1, len(pairs) + 1)):
            raise JudgeError("judge did not return exactly one result per pair")
        return [{"backed": by_no[i]["backed"], "reason": str(by_no[i].get("reason", ""))}
                for i in range(1, len(pairs) + 1)]

    def relevance(self, question, answer):
        r = self._run(RELEVANCE_TASK, f"Question: {question}\n\nAnswer: {answer}")
        if not isinstance(r.get("relevant"), bool):
            raise JudgeError("relevant must be true or false")
        return {"relevant": r["relevant"], "reason": str(r.get("reason", ""))}
