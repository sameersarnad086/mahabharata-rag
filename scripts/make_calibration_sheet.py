"""Build the blind grading sheet for judge calibration from a saved end-to-end run.

Picks 12 answers spread over the judge's own verdicts (so the sample includes good, bad, partly right and refusals),
writes eval/calibration_sheet.md (judge scores NOT shown) and eval/results/calibration_key.json (the judge's scores,
for the comparison afterwards). Selection is fixed by rules, not by me eyeballing, so it can be reproduced.
Usage: python scripts/make_calibration_sheet.py baseline_working
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag import eval_generation as E
from src.rag.retrieval import Retriever

name = sys.argv[1] if len(sys.argv) > 1 else "baseline_working"
data = json.load(open(config.ROOT / "eval" / "results" / f"gen_{name}.json"))
recs = [r for r in data["records"]["end-to-end"] if "error" not in r]
qs = {q["id"]: q for q in E.load_questions()}

def pick(pred, n, used):
    out = [r for r in recs if r["id"] not in used and pred(r)][:n]
    used.update(r["id"] for r in out)
    return out

used, chosen = set(), []
chosen += pick(lambda r: r["outcome"] == "false_refusal_retrieval", 1, used)         # a wrongful refusal
chosen += pick(lambda r: r["outcome"] == "correct_refusal", 2, used)                 # judged-as-correct refusals
chosen += pick(lambda r: r.get("correctness") == 0.0, 1, used)                       # judge says wrong
chosen += pick(lambda r: r.get("correctness") == 0.5, 2, used)                       # judge says partly right
chosen += pick(lambda r: (r.get("faithfulness") or 1) < 0.9 and r.get("correctness") == 1.0, 2, used)  # right but unfaithful claims
chosen += pick(lambda r: (r.get("citation_support") if r.get("citation_support") is not None else 1) < 0.5, 1, used)  # weak citations
chosen += pick(lambda r: r.get("correctness") == 1.0 and r.get("faithfulness") == 1.0 and r.get("citation_support") == 1.0, 3, used)  # clean ones
chosen += pick(lambda r: r.get("correctness") in (0.5, 0.0, 1.0), 12 - len(chosen), used)   # top up to 12
chosen = chosen[:12]

ret = Retriever()
sheet = ["# Judge calibration sheet (blind)\n",
         "Grade each item yourself using ONLY the passages shown. You do not see the judge's scores.\n",
         "For each item fill in the three lines at the end:",
         "- **Correct?** yes / partly / no  (compare the answer with the expected answer; a refusal on an answerable question is *no*; a refusal on an unanswerable question is *yes*)",
         "- **Supported?** for each sentence of the answer: does the passage text really say it? (yes / no per sentence, e.g. `1 yes, 2 no`; write `n/a` for a refusal)",
         "- **Citations ok?** for each sentence with a [n]: does passage n really back that sentence? (e.g. `1 yes, 2 no`; `n/a` if none)\n",
         "Do not use outside knowledge: a true fact that is not in the passages counts as *not supported*.\n"]
key = []
for i, r in enumerate(chosen, 1):
    q = qs[r["id"]]
    hits = ret.search(q["question"], config.TOP_K)
    sheet.append(f"\n---\n\n## Item {i}  ({r['id']})\n\n**Question:** {q['question']}\n")
    exp = q.get("expected_answer") or q.get("expected") or "(no answer exists in the text: the system should refuse)"
    sheet.append(f"**Expected answer:** {exp}\n\n**System's answer:** {r['answer']}\n\n**Passages the system saw:**\n")
    for h in hits:
        sheet.append(f"[{h.rank}] ({h.citation}) {' '.join(h.text.split())}\n")
    sheet.append("\n**Correct?** \n\n**Supported?** \n\n**Citations ok?** \n")
    key.append({"item": i, "id": r["id"], "outcome": r["outcome"],
                "judge": {k: r.get(k) for k in ("correctness", "faithfulness", "citation_support", "relevance")},
                "judge_claims": r.get("judge", {}).get("claims"), "judge_citations": r.get("judge", {}).get("citations")})
(config.ROOT / "eval" / "calibration_sheet.md").write_text("\n".join(sheet), encoding="utf-8")
(config.ROOT / "eval" / "results" / "calibration_key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(chosen), "items:", [c["id"] for c in chosen])
