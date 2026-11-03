"""Pick the fresh calibration items for round 2 (answers not used in round 1). Fixed rules, no judging by eye:
first every unused answerable answer where the judge gave any score below 1 (so the sample contains judge-flagged cases),
then the first unused clean answers, then one correct refusal; 8 items in total, at most 5 flagged.
Writes only ids + judge scores to eval/results/calibration_key_round2.json (the scores stay hidden from the form).
Usage: python scripts/pick_round2.py baseline_working
"""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
recs = [r for r in json.load(open(root / "eval/results" / f"gen_{sys.argv[1]}.json"))["records"]["end-to-end"] if "error" not in r]
used = {k["id"] for k in json.load(open(root / "eval/results/calibration_key.json"))}
fresh = [r for r in recs if r["id"] not in used]
score = lambda r: [r.get(k) for k in ("correctness", "faithfulness", "citation_support")]
flagged = [r for r in fresh if r["outcome"] == "answered" and any(v is not None and v < 1 for v in score(r))][:5]
clean = [r for r in fresh if r["outcome"] == "answered" and r not in flagged and all(v == 1 for v in score(r))][:2]
refusal = [r for r in fresh if r["outcome"] == "correct_refusal"][:1]
chosen = (flagged + clean + refusal)
chosen += [r for r in fresh if r["outcome"] == "answered" and r not in chosen][:8 - len(chosen)]
out = [{"item": i, "id": r["id"], "outcome": r["outcome"], "judge": {k: r.get(k) for k in ("correctness", "faithfulness", "citation_support")},
        "judge_claims": (r.get("judge") or {}).get("claims"), "judge_citations": (r.get("judge") or {}).get("citations")} for i, r in enumerate(chosen, 1)]
json.dump(out, open(root / "eval/results/calibration_key_round2.json", "w"), indent=1, ensure_ascii=False)
print([c["id"] for c in out])
