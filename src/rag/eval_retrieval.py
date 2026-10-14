"""Score the retriever on the labelled question set (eval/retrieval_questions.csv).

Two ways to decide whether a retrieved chunk is a HIT for a question:
  section check : the chunk touches at least one gold section (coarse, generous)
  phrase check  : the chunk's text contains at least one evidence phrase word for word (strict)

Optional variant: exclude_summaries drops the book's summary passages (Sections 1, 2, 95) from the
labels, to see how much of the score comes from those easy targets. Questions that have no
non-summary gold are left out of that variant.
"""
import csv
import json
import re
from dataclasses import dataclass, field

import config
from src.rag import metrics as M
from src.rag.textnorm import norm

SUMMARY_SECTIONS = {1, 2, 95}
KS = (1, 3, 5, 10)
CHECKS = ("section", "phrase")


@dataclass
class QResult:
    id: str
    type: str
    split: str
    band: str
    question: str
    first_rank: dict = field(default_factory=dict)       # check -> rank of first hit (None if none in top 10)
    scores: dict = field(default_factory=dict)           # check -> {"hit@5": x, ...}
    top_sections: list = field(default_factory=list)     # sections of the top-5 chunks, for inspection


def load_questions():
    with open(config.ROOT / "eval" / "retrieval_questions.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _labels(q, section_text, exclude_summaries):
    gold = {int(x) for x in re.split(r"[,\s]+", q["gold_sections"].strip()) if x}
    phrases = [p.strip() for p in q["evidence_phrases"].split("||") if p.strip()]
    if exclude_summaries:
        gold -= SUMMARY_SECTIONS
        if not gold:
            return None
        blob = norm(" ".join(section_text.get(g, "") for g in gold))
        phrases = [p for p in phrases if norm(p) in blob]
        if not phrases:
            return None
    return gold, phrases


def evaluate(retriever, questions, exclude_summaries=False):
    chunks = retriever.chunks
    csec = [set(c["section_numbers"]) for c in chunks]
    ctext = [norm(c["text"]) for c in chunks]
    paras = [json.loads(l) for l in open(config.PROCESSED_DIR / "paragraphs.jsonl", encoding="utf-8")]
    section_text = {}
    for p in paras:
        section_text.setdefault(p["section_number"], []).append(p["text"])
    section_text = {k: " ".join(v) for k, v in section_text.items()}

    results, dropped = [], []
    for q in questions:
        lab = _labels(q, section_text, exclude_summaries)
        if lab is None:
            dropped.append(q["id"])
            continue
        gold, phrases = lab
        nphr = [norm(p) for p in phrases]
        hits = retriever.search(q["question"], max(KS))
        ids = [h.chunk_id for h in hits]
        is_hit = {
            "section": lambda i: bool(csec[i] & gold),
            "phrase": lambda i: any(p in ctext[i] for p in nphr),
        }
        n_rel = {c: sum(is_hit[c](i) for i in range(len(chunks))) for c in CHECKS}
        r = QResult(q["id"], q["type"], q["split"], q["band"], q["question"],
                    top_sections=[sorted(csec[i]) for i in ids[:5]])
        for c in CHECKS:
            flags = [is_hit[c](i) for i in ids]
            r.first_rank[c] = next((rk for rk, f in enumerate(flags, 1) if f), None)
            s = {}
            for k in KS:
                top = ids[:k]
                if c == "section":
                    found = len(gold & set().union(*[csec[i] for i in top]))
                    total = len(gold)
                else:
                    joined = " ".join(ctext[i] for i in top)
                    found = sum(p in joined for p in nphr)
                    total = len(nphr)
                s[f"hit@{k}"] = M.hit_at_k(flags, k)
                s[f"precision@{k}"] = M.precision_at_k(flags, k)
                s[f"recall@{k}"] = M.recall_at_k(found, total)
                s[f"mrr@{k}"] = M.reciprocal_rank(flags[:k])
                s[f"ndcg@{k}"] = M.ndcg_at_k(flags, k, n_rel[c])
            r.scores[c] = s
        results.append(r)
    return results, dropped


def mean(results, check, metric):
    vals = [r.scores[check][metric] for r in results]
    return sum(vals) / len(vals) if vals else float("nan")


def summarise(results):
    out = {"n": len(results)}
    for c in CHECKS:
        out[c] = {m: mean(results, c, m) for m in results[0].scores[c]} if results else {}
        out[c]["hits_at_5"] = int(sum(r.scores[c]["hit@5"] for r in results))
    return out
