"""Assign each retrieval question to the 'working' or 'held-out' group, once, by a fixed rule.

Rule (fixed before any question has been scored):
  - Held-out size per question type is fixed below (12 of 36 in total).
  - Questions that share a `unit` (the name pairs) always go to the same group.
  - Draw units at random within each type with random.Random(seed), trying seeds 1, 2, 3...
    and take the FIRST seed for which each third of the book (early/middle/late) has
    between 3 and 5 held-out questions.
  - Once assigned the split is frozen: rerunning does nothing unless --force is given.

Usage: python scripts/make_split.py            (assign, if not already assigned)
       python scripts/make_split.py --check    (verify the frozen split and print balance)
"""
import argparse
import collections
import csv
import json
import random
import sys
from pathlib import Path

CSV = Path(__file__).resolve().parent.parent / "eval" / "retrieval_questions.csv"
INFO = CSV.with_name("split_info.json")
HELD_OUT_PER_TYPE = {"plain": 3, "paraphrase": 1, "alias": 2, "spelling": 1,
                     "lineage": 2, "multihop": 2, "ambiguous": 1}
BAND_RANGE = (3, 5)   # allowed held-out questions per third of the book


def load():
    with open(CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows):
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def draw(rows, seed):
    rng = random.Random(seed)
    held = set()
    for typ, n_questions in HELD_OUT_PER_TYPE.items():
        units = collections.OrderedDict()
        for r in rows:
            if r["type"] == typ:
                units.setdefault(r["unit"], []).append(r["id"])
        order = list(units)
        rng.shuffle(order)
        taken = 0
        for u in order:
            if taken + len(units[u]) <= n_questions:
                held.update(units[u])
                taken += len(units[u])
            if taken == n_questions:
                break
        assert taken == n_questions, f"cannot fill {typ}"
    return held


def balance(rows, held):
    band = collections.Counter(r["band"] for r in rows if r["id"] in held)
    return band


def report(rows):
    print(f"{'type':11s} {'working':>8s} {'held-out':>9s}")
    for typ in HELD_OUT_PER_TYPE:
        w = sum(r["type"] == typ and r["split"] == "working" for r in rows)
        h = sum(r["type"] == typ and r["split"] == "held-out" for r in rows)
        print(f"{typ:11s} {w:8d} {h:9d}")
    print(f"{'TOTAL':11s} {sum(r['split']=='working' for r in rows):8d} {sum(r['split']=='held-out' for r in rows):9d}")
    print(f"\n{'book third':11s} {'working':>8s} {'held-out':>9s}")
    for b in ("early", "middle", "late"):
        w = sum(r["band"] == b and r["split"] == "working" for r in rows)
        h = sum(r["band"] == b and r["split"] == "held-out" for r in rows)
        print(f"{b:11s} {w:8d} {h:9d}")


def check(rows):
    ok = True
    def t(name, cond):
        nonlocal ok
        print(("PASS" if cond else "FAIL"), name); ok &= cond
    t("every question has a split", all(r["split"] in ("working", "held-out") for r in rows))
    t("12 held-out, 24 working", sum(r["split"] == "held-out" for r in rows) == 12)
    units = collections.defaultdict(set)
    for r in rows:
        units[r["unit"]].add(r["split"])
    t("name pairs are never separated", all(len(s) == 1 for s in units.values()))
    for typ, n in HELD_OUT_PER_TYPE.items():
        t(f"held-out count for {typ} is {n}", sum(r["type"] == typ and r["split"] == "held-out" for r in rows) == n)
    band = collections.Counter(r["band"] for r in rows if r["split"] == "held-out")
    t(f"each third of the book has {BAND_RANGE[0]}-{BAND_RANGE[1]} held-out questions {dict(band)}",
      all(BAND_RANGE[0] <= band[b] <= BAND_RANGE[1] for b in ("early", "middle", "late")))
    if INFO.exists():
        seed = json.loads(INFO.read_text())["seed"]
        t(f"split reproduces from the recorded seed ({seed})",
          {r["id"] for r in rows if r["split"] == "held-out"} == draw(rows, seed))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    rows = load()
    if args.check:
        report(rows); print(); sys.exit(0 if check(rows) else 1)
    if any(r["split"] for r in rows) and not args.force:
        print("Split already assigned and frozen. Use --check to inspect it."); return
    for seed in range(1, 1000):
        held = draw(rows, seed)
        band = balance(rows, held)
        if all(BAND_RANGE[0] <= band[b] <= BAND_RANGE[1] for b in ("early", "middle", "late")):
            break
    for r in rows:
        r["split"] = "held-out" if r["id"] in held else "working"
    save(rows)
    INFO.write_text(json.dumps({"seed": seed, "rule": __doc__.split("Rule")[1].split("Usage")[0].strip(),
                                "held_out_per_type": HELD_OUT_PER_TYPE, "band_range": BAND_RANGE}, indent=2))
    print(f"assigned using seed {seed}\n"); report(rows)


if __name__ == "__main__":
    main()
