"""Check that each unanswerable question (eval/generation_questions.csv) really has no answer in the text.

For each question it searches every paragraph for keywords. 'expect 0' rows must find nothing. 'review'
rows are tolerated mentions (for example a one-line mention in a summary passage) and are printed so a
human can confirm they do not answer the question.
Usage: python scripts/verify_unanswerable.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# id -> (what we search: every pattern must match in the same paragraph, expectation)
CHECKS = {
    "G01": ([r"Mahaprasthanika|Himalaya", r"dropped|fell"], "review"),
    "G02": ([r"Bhagavat|\bGita\b"], "review"),
    "G03": ([r"Hanuman"], "review"),
    "G04": ([r"Devadatta"], 0),
    "G05": ([r"Draupadi|Panchali", r"years old|years of age|\bage of"], 0),
    # not plain 'Krishna': that is also one of Draupadi's own names ('born Krishna (Draupadi)', Section 63).
    # Reviewed by eye: the 3 hits are Sakuni's curse (Sec 63) and Pandu's curse (Sec 95), nothing about Krishna.
    "G06": ([r"Gandhari", r"Vasudeva|Kesava|Madhava|Janardana|Govinda", r"curs"], "review"),
    "G07": ([r"Ramayana"], 0),
    "G08": ([r"Mughal|Babur"], 0),
}


def main():
    paras = [json.loads(l) for l in open(config.PROCESSED_DIR / "paragraphs.jsonl", encoding="utf-8")]
    bad = False
    for qid, (pats, expect) in CHECKS.items():
        hits = [p for p in paras if all(re.search(x, p["text"], re.I) for x in pats)]
        status = "ok" if expect == "review" or len(hits) == expect else "FAIL"
        bad |= status == "FAIL"
        print(f"{qid} {status:4s} {len(hits)} paragraph(s) match {pats}")
        if expect == "review":
            for p in hits[:3]:
                m = re.search(pats[0], p["text"], re.I)
                a = max(0, m.start() - 150)
                print(f"      [Section {p['section_number']}] ...{p['text'][a:a + 320]}...")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
