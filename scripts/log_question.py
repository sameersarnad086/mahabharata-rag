"""Run a question through the full pipeline and append a detailed entry to QUESTION_LOG.md.

Each entry records: the question, the model's answer, the 5 retrieved chunks (rank, score, chunk id,
section, file, opening text, whether the answer cited it), and a verdict written by a person.
These are informal explorations, NOT the Phase 2 evaluation set.

Usage: python scripts/log_question.py "question" --verdict "..." [--notes "..."] [--label Q7]
"""
import argparse
import datetime
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.generation import generate_answer
from src.rag.retrieval import Retriever

LOG = config.ROOT / "QUESTION_LOG.md"
HEADER = """# QUESTION_LOG.md

Informal questions asked of the Phase 1 baseline, with the full result and a human verdict.
These are exploration notes, **not** the Phase 2 evaluation set (which is written separately and never edited to flatter results).

Setup for all entries: fixed-size chunks (1000 chars, 200 overlap), `BAAI/bge-small-en-v1.5` embeddings, top-5 cosine retrieval,
`gemini-3.1-flash-lite` (temperature 0). Section numbers are the printed heading numbers; the file name is always heading + 1.
Chunk ids are positions in `data/processed/chunks.jsonl` and change if chunking changes.

"""


def one_line(text: str, n: int = 190) -> str:
    return re.sub(r"\s+", " ", text)[:n].replace("|", "/")


def log_question(retriever, question: str, verdict: str, notes: str = "", label: str | None = None, k: int = 5) -> str:
    hits = retriever.search(question, k)
    ans = generate_answer(question, hits)
    if not LOG.exists():
        LOG.write_text(HEADER, encoding="utf-8")
    label = label or f"Q{LOG.read_text(encoding='utf-8').count('\n## Q') + 1}"
    lines = [f"\n## {label}. {question}", f"_Run on {datetime.date.today()}_\n",
             "**Answer given:**", "", "> " + (ans.text.replace("\n", "\n> ") or "(empty)"), "",
             f"Tokens: prompt {ans.prompt_tokens}, output {ans.output_tokens}. "
             f"Citations in answer: {ans.cited or 'none'}"
             + (f" (INVALID: {ans.invalid_citations})" if ans.invalid_citations else ""), "",
             "**Top-5 chunks retrieved:**", ""]
    for h in hits:
        c = retriever.chunks[h.chunk_id]
        secs = ", ".join(str(n) for n in c["section_numbers"]) or c["sections"][0]
        mark = "**CITED**" if h.rank in ans.cited else "not cited"
        lines.append(f"{h.rank}. score {h.score:.3f} | chunk {h.chunk_id} | Section {secs} ({'; '.join(c['sub_parvas'])}) | "
                     f"`{c['first_file']}` para {c['first_para_index']} | {mark}")
        lines.append(f"   - starts: \"{one_line(h.text)}...\"")
    lines += ["", f"**Verdict:** {verdict}"]
    if notes:
        lines += ["", f"**Notes:** {notes}"]
    lines.append("\n---")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return label


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--verdict", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--label")
    args = ap.parse_args()
    print("logged as", log_question(Retriever(), args.question, args.verdict, args.notes, args.label))


if __name__ == "__main__":
    main()
