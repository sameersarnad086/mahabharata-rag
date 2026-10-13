"""Full RAG: retrieve the top-k chunks, then have the language model answer from them.

Usage: python scripts/ask.py "Why did Bhishma take a vow of celibacy?" [-k 5] [--dry-run]
  --dry-run  build and print the prompt but do not call the model (no API key needed)
"""
import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.generation import build_prompt, generate_answer
from src.rag.retrieval import Retriever


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("-k", type=int, default=config.TOP_K)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    hits = Retriever().search(args.question, args.k)
    if args.dry_run:
        system, user = build_prompt(args.question, hits)
        print("=== SYSTEM ===\n" + system + "\n\n=== USER ===\n" + user)
        return

    ans = generate_answer(args.question, hits)
    print(f"\n{ans.text}\n")
    print(f"model={ans.model}  tokens: prompt={ans.prompt_tokens} output={ans.output_tokens} thinking={ans.thinking_tokens}")
    if ans.invalid_citations:
        print(f"WARNING: answer cites passages that were not provided: {ans.invalid_citations}")
    print("\nSources:")
    for h in hits:
        mark = "cited" if h.rank in ans.cited else "     "
        print(f"  [{h.rank}] {mark}  score={h.score:.3f}  {h.citation}")


if __name__ == "__main__":
    main()
