"""Score the generator on the labelled questions: the logic around the judge.

Everything here that does not need a model is plain code: loading questions, picking the ideal-context
passages, spotting refusals, splitting an answer into cited sentences, and turning judge replies into
scores. The judge itself lives in judge.py.

Two modes:
  end-to-end    : passages come from the real retriever (top TOP_K)
  ideal-context : passages are the gold chunks (those containing an evidence phrase), handed over directly

Per answer, the scores are:
  correctness      1 / 0.5 / 0 against the expected answer (a refusal to an answerable question scores 0)
  faithfulness     supported claims / all claims
  citation_support backed cited sentences / all cited sentences
  relevance        1 / 0 (refusals are not scored)
  refused          did it use the fixed refusal sentence (plain string match)
"""
import csv
import re
from collections import Counter
from dataclasses import dataclass

import config
from src.rag.generation import CITATION, check_citations
from src.rag.judge import passages_text
from src.rag.textnorm import norm

REFUSAL_SENTENCE = "The provided passages do not answer this question."
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[\"'(A-Z0-9])|\n+")


@dataclass
class Passage:
    """Same fields as retrieval.Hit that the prompt and the judge use."""
    rank: int
    score: float
    chunk_id: int
    citation: str
    text: str


def load_questions():
    """The 36 retrieval questions (all answerable) plus the unanswerable ones, in one list."""
    rows = []
    with open(config.ROOT / "eval" / "retrieval_questions.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["answerable"] = "yes"
            rows.append(r)
    path = config.ROOT / "eval" / "generation_questions.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    return rows


def split_phrases(cell):
    return [p.strip() for p in (cell or "").split("||") if p.strip()]


def is_refusal(text):
    return norm(REFUSAL_SENTENCE) in norm(text)


def gold_found(hits, phrases):
    """True if any evidence phrase appears word for word in any of the passages."""
    texts = [norm(h.text) for h in hits]
    return any(norm(p) in t for p in phrases for t in texts)


def pick_ideal_passages(chunks, phrases, k):
    """The gold chunks: chunks containing at least one evidence phrase, those covering more phrases first."""
    from src.rag.retrieval import make_citation
    nphr = [norm(p) for p in phrases]
    scored = []
    for i, c in enumerate(chunks):
        t = norm(c["text"])
        n = sum(p in t for p in nphr)
        if n:
            scored.append((-n, i))
    chosen = [i for _, i in sorted(scored)[:k]]
    return [Passage(rank=r, score=1.0, chunk_id=i, citation=make_citation(chunks[i]), text=chunks[i]["text"])
            for r, i in enumerate(sorted(chosen), 1)]


def split_cited_sentences(text):
    """[(sentence, [passage numbers it cites])] for every sentence that carries a [n] marker.
    Limitation: a marker placed AFTER the full stop ('... Menaka. [2]') stays with the next sentence."""
    out = []
    for s in (p.strip() for p in SENT_SPLIT.split(text)):
        nums = list(dict.fromkeys(int(n) for n in CITATION.findall(s)))
        if nums:
            out.append((s, nums))
    return out


def classify(answerable, refused, mode, found):
    if answerable:
        if not refused:
            return "answered"
        if mode == "end-to-end" and not found:
            return "false_refusal_retrieval"      # the gold text never reached the model
        return "false_refusal_generation"         # the gold text was there and it still refused
    return "correct_refusal" if refused else "should_have_refused"


def score_answer(q, hits, answer_text, judge, mode):
    """Turn one generated answer into a record of scores (calling the judge where code cannot decide)."""
    answerable = q["answerable"] == "yes"
    phrases = split_phrases(q.get("evidence_phrases"))
    found = gold_found(hits, phrases) if answerable else None
    refused = is_refusal(answer_text)
    _, invalid = check_citations(answer_text, len(hits))
    rec = {"id": q["id"], "type": q["type"], "split": q["split"], "mode": mode, "answerable": answerable,
           "question": q["question"], "answer": answer_text, "refused": refused, "gold_found": found,
           "outcome": classify(answerable, refused, mode, found), "invalid_citations": invalid,
           "correctness": None, "relevance": None, "faithfulness": None, "citation_support": None,
           "n_claims": 0, "n_cited_sentences": 0, "judge": {}}
    if refused:
        if answerable:
            rec["correctness"] = 0.0
        return rec

    if answerable:
        c = judge.correctness(q["question"], q["expected_answer"], answer_text)
        rec["correctness"], rec["judge"]["correctness"] = c["score"], c
        rel = judge.relevance(q["question"], answer_text)
        rec["relevance"], rec["judge"]["relevance"] = float(rel["relevant"]), rel

    claims = judge.extract_claims(answer_text)
    rec["n_claims"] = len(claims)
    if claims:
        verdicts = judge.verify_claims(hits, claims)
        rec["faithfulness"] = sum(v["supported"] for v in verdicts) / len(verdicts)
        rec["judge"]["claims"] = verdicts

    by_rank = {h.rank: h for h in hits}
    sentences = split_cited_sentences(answer_text)
    rec["n_cited_sentences"] = len(sentences)
    if sentences:
        results = [None] * len(sentences)
        to_judge = []
        for i, (s, nums) in enumerate(sentences):
            if any(n not in by_rank for n in nums):
                results[i] = {"backed": False, "reason": "cites a passage number that does not exist"}
            else:
                to_judge.append((i, (s, passages_text([by_rank[n] for n in nums]))))
        if to_judge:
            for (i, _), r in zip(to_judge, judge.citations([p for _, p in to_judge])):
                results[i] = r
        rec["citation_support"] = sum(r["backed"] for r in results) / len(results)
        rec["judge"]["citations"] = [{"sentence": s, **r} for (s, _), r in zip(sentences, results)]
    return rec


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def summarise(records):
    ok = [r for r in records if not r.get("error")]
    ans = [r for r in ok if r["answerable"]]
    una = [r for r in ok if not r["answerable"]]
    answered = [r for r in ok if not r["refused"]]
    outcomes = Counter(r["outcome"] for r in ok)
    return {
        "n": len(records), "n_errors": len(records) - len(ok), "n_answerable": len(ans), "n_unanswerable": len(una),
        "correctness": _mean(r["correctness"] for r in ans),
        "correctness_when_answered": _mean(r["correctness"] for r in ans if not r["refused"]),
        "faithfulness": _mean(r["faithfulness"] for r in answered),
        "citation_support": _mean(r["citation_support"] for r in answered),
        "relevance": _mean(r["relevance"] for r in ans if not r["refused"]),
        "gold_found_rate": _mean(float(r["gold_found"]) for r in ans if r["gold_found"] is not None),
        "outcomes": dict(outcomes),
        "refusal": {
            "correct_refusals": outcomes["correct_refusal"], "unanswerable": len(una),
            "false_refusals": outcomes["false_refusal_retrieval"] + outcomes["false_refusal_generation"],
            "answerable": len(ans),
        },
    }


def by_type(records):
    groups = {}
    for r in records:
        if not r.get("error") and r["answerable"]:
            groups.setdefault(r["type"], []).append(r)
    return {t: {"n": len(rs), "correctness": _mean(x["correctness"] for x in rs),
                "faithfulness": _mean(x["faithfulness"] for x in rs if not x["refused"]),
                "refused": sum(x["refused"] for x in rs)} for t, rs in groups.items()}
