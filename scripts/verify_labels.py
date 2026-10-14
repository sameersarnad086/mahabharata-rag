"""Check the gold labels in eval/retrieval_questions.csv against the actual text.

For every question that has evidence phrases it checks, mechanically:
  1. every gold section number exists in the corpus;
  2. each evidence phrase appears word for word (ignoring capitals, extra spaces, curly quotes) in the
     paragraphs of at least one gold section;
  3. each evidence phrase sits entirely inside at least one chunk that touches a gold section, so
     chunking cannot cut it in half and make a correct chunk look like a miss.
Evidence phrases are separated by ' || ' in the CSV; gold sections by commas.

Usage: python scripts/verify_labels.py [R01 R02 ...]   (default: every question with phrases)
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def main() -> int:
    rows = list(csv.DictReader(open(ROOT / "eval" / "retrieval_questions.csv", newline="", encoding="utf-8")))
    paras = [json.loads(l) for l in open(ROOT / "data" / "processed" / "paragraphs.jsonl", encoding="utf-8")]
    chunks = [json.loads(l) for l in open(ROOT / "data" / "processed" / "chunks.jsonl", encoding="utf-8")]
    wanted = set(sys.argv[1:])
    bad = 0
    for r in rows:
        if wanted and r["id"] not in wanted:
            continue
        if not r["evidence_phrases"].strip():
            continue
        gold = [int(x) for x in re.split(r"[,\s]+", r["gold_sections"].strip()) if x]
        phrases = [p.strip() for p in r["evidence_phrases"].split("||") if p.strip()]
        sec_text = {g: norm(" ".join(p["text"] for p in paras if p["section_number"] == g)) for g in gold}
        print(f"{r['id']}  gold sections {gold}")
        for g in gold:
            if not sec_text[g]:
                print(f"   FAIL section {g} does not exist"); bad += 1
        for ph in phrases:
            n = norm(ph)
            in_sections = [g for g in gold if n in sec_text[g]]
            in_chunks = [c["chunk_id"] for c in chunks
                         if n in norm(c["text"]) and set(c["section_numbers"]) & set(gold)]
            ok = bool(in_sections) and bool(in_chunks)
            bad += not ok
            print(f"   {'PASS' if ok else 'FAIL'}  \"{ph[:70]}{'...' if len(ph) > 70 else ''}\"  "
                  f"found in section(s) {in_sections or 'NONE'}, in {len(in_chunks)} chunk(s) {in_chunks[:4]}")
    print(f"\n{'ALL PASS' if not bad else str(bad) + ' PROBLEM(S)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
