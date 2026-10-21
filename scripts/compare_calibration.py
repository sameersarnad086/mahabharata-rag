"""Compare the owner's calibration grades with the judge's scores from a saved run.

Usage: python scripts/compare_calibration.py <run_name> [grades_file]
Reads eval/results/gen_<run_name>.json and the owner's grades (default eval/calibration_grades.md).
Three agreement figures: correctness (yes/partly/no vs 1/0.5/0), 'all sentences supported' per answer
(owner) vs judge faithfulness == 1, and citation backing per cited sentence.
"""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
run = sys.argv[1]
grades = (Path(sys.argv[2]) if len(sys.argv) > 2 else root / "eval" / "calibration_grades.md").read_text()
recs = {r["id"]: r for r in json.load(open(root / "eval" / "results" / f"gen_{run}.json"))["records"]["end-to-end"]}
SC = {"yes": 1.0, "partly": 0.5, "no": 0.0}
corr = [0, 0]; sup = [0, 0]; cit = [0, 0]
for m in re.finditer(r"^Item (\d+) \((\w+)\): Correct=(\S+) \| Supported: (.*?) \| Citations: (.*?)(?: \| Note:.*)?$", grades, re.M):
    n, qid, c, s, ci = m.groups(); r = recs.get(qid)
    if not r or "error" in r:
        print(f"{qid}: missing"); continue
    line = [f"{qid:4s}"]
    if r["outcome"] == "correct_refusal":
        ok = c == "yes"; corr[0] += ok; corr[1] += 1; line.append(f"corr owner={c} judge=refusal-ok {'AGREE' if ok else 'DIFF'}")
    elif r.get("correctness") is None:
        line.append(f"corr owner={c} judge=not scored (refusal on answerable)")
    else:
        ok = SC[c] == r["correctness"]; corr[0] += ok; corr[1] += 1
        line.append(f"corr owner={c} judge={r['correctness']} {'AGREE' if ok else 'DIFF'}")
    if r.get("faithfulness") is not None:
        owner_all = all(x.split()[1] == "yes" for x in s.split(", "))
        ok = owner_all == (r["faithfulness"] == 1.0); sup[0] += ok; sup[1] += 1
        line.append(f"supp owner_all={owner_all} judge_faith={r['faithfulness']:.2f} {'AGREE' if ok else 'DIFF'}")
    jc = (r.get("judge") or {}).get("citations") or []
    oc = [x.split()[1] == "yes" for x in ci.split(", ")] if ci != "n/a" else []
    if jc and len(jc) == len(oc):
        for o, j in zip(oc, jc):
            cit[0] += (o == j["backed"]); cit[1] += 1
        line.append("cite " + ",".join("ok" if o == j["backed"] else "DIFF" for o, j in zip(oc, jc)))
    print(" | ".join(line))
pct = lambda a: f"{a[0]}/{a[1]} = {a[0] / a[1]:.0%}" if a[1] else "-"
print(f"\ncorrectness {pct(corr)}   all-supported {pct(sup)}   citations {pct(cit)}")
