"""Build eval/calibration_form.html: the same 12 blind items as eval/calibration_sheet.md, but as a fillable form.

Reads the item ids from eval/results/calibration_key.json (ids only, never the judge's scores), rebuilds each item's
question, expected answer, answer and passages, and embeds them in one self-contained HTML page. The page autosaves
in the browser and has a button that copies all grades and notes as text to paste back into the chat.
Usage: python scripts/make_calibration_form.py [run_name] [key_file] [out_html] [title]
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
key_file = sys.argv[2] if len(sys.argv) > 2 else "calibration_key.json"
out_html = sys.argv[3] if len(sys.argv) > 3 else "calibration_form.html"
title = sys.argv[4] if len(sys.argv) > 4 else "Judge Calibration Form"
data = json.load(open(config.ROOT / "eval" / "results" / f"gen_{name}.json"))
recs = {r["id"]: r for r in data["records"]["end-to-end"]}
ids = [k["id"] for k in json.load(open(config.ROOT / "eval" / "results" / key_file))]
qs = {q["id"]: q for q in E.load_questions()}
ret = Retriever()
items = []
for n, qid in enumerate(ids, 1):
    q = qs[qid]
    hits = ret.search(q["question"], config.TOP_K)
    sents = [s.strip() for s in E.SENT_SPLIT.split(recs[qid]["answer"]) if s and s.strip()]
    items.append({"n": n, "id": qid, "question": q["question"],
                  "expected": q.get("expected_answer") or "No answer exists in the text. The system should refuse.",
                  "sentences": sents,
                  "passages": [{"rank": h.rank, "cite": h.citation.replace("Mahabharata (Ganguli), ", ""), "text": " ".join(h.text.split())} for h in hits]})

page = open(config.ROOT / "scripts" / "calibration_form_template.html", encoding="utf-8").read()
page = page.replace("Judge Calibration Form", title).replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/"))
(config.ROOT / "eval" / out_html).write_text(page, encoding="utf-8")
print("wrote eval/" + out_html + " with", len(items), "items")
