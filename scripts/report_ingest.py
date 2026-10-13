"""Sanity-check the full ingestion output (data/processed/paragraphs.jsonl)."""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(s: str) -> int:
    t = 0
    for a, b in zip(s, s[1:] + " "):
        t += -ROMAN[a] if ROMAN.get(b, 0) > ROMAN[a] else ROMAN[a]
    return t


rows = [json.loads(l) for l in open(config.PROCESSED_DIR / "paragraphs.jsonl", encoding="utf-8")]
by_file = collections.defaultdict(list)
for r in rows:
    by_file[r["file"]].append(r)

print(f"files={len(by_file)} paragraphs={len(rows)} chars={sum(len(r['text']) for r in rows)} "
      f"merged_fragments={sum(r['merged'] for r in rows)}")

bad_heading, seq_gaps, prev = [], [], 0
for f, ps in sorted(by_file.items()):
    h = ps[0]["heading"]
    m = re.fullmatch(r"SECTION ([IVXLC]+)", h)
    if not m:
        bad_heading.append((f, h)); continue
    n = roman(m.group(1))
    if n != prev + 1:
        seq_gaps.append((f, h, prev))
    prev = n
mismatch = [(f, ps[0]["heading"], ps[0].get("section_number")) for f, ps in sorted(by_file.items())
            if int(f[8:11]) >= 2 and ps[0].get("section_number") != int(f[8:11]) - 1]
print("section_number != file number - 1 (should be none):", mismatch)
print("non-SECTION headings:", bad_heading)
print("section sequence gaps:", seq_gaps, "| last section number:", prev)

sp = collections.Counter(r["sub_parva"] for r in rows if r["para_index"] == 0)
print("files whose FIRST paragraph already has a sub_parva:", sum(sp.values()), "of", len(by_file))
labels = collections.Counter(r["sub_parva"] for r in rows)
print("distinct sub_parva labels:", len(labels))
for k, v in labels.most_common(): print(f"  {v:5d} paras  {k!r}")

short = [r for r in rows if len(r["text"]) < 25]
lower = [r for r in rows if r["text"][:1].islower()]
mojibake = [r for r in rows if re.search(r"[âÃ][\x80-\xbf€™œ]", r["text"])]
junk = [r for r in rows if re.search(r"Comments and social|bookmarks|Copyright ©|Evinity", r["text"])]
print(f"short(<25 chars)={len(short)} lowercase-start={len(lower)} mojibake={len(mojibake)} UI-junk={len(junk)}")
for name, lst in (("short", short), ("lowercase-start", lower)):
    for r in lst[:6]: print(f"  {name}: {r['file']} [{r['para_index']}] {r['text'][:80]!r}")
