"""Ask a question; print the top-k retrieved chunks with scores and citations.

Usage: python scripts/search.py "Who was the father of Bhishma?" [-k 5]
"""
import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.retrieval import Retriever


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("-k", type=int, default=config.TOP_K)
    args = ap.parse_args()
    for h in Retriever().search(args.question, args.k):
        print(f"\n#{h.rank}  score={h.score:.3f}  chunk {h.chunk_id}\n    {h.citation}\n    {h.text[:300]}...")


if __name__ == "__main__":
    main()
