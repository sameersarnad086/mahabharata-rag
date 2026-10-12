"""Chunk the cleaned corpus with the configured size/overlap and print stats.

Writes data/processed/chunks.jsonl. Usage: python scripts/run_chunking.py
"""
import json
import statistics as st
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.chunking import build_chunks, load_paragraphs


def main() -> None:
    chunks = build_chunks(load_paragraphs())
    out = config.PROCESSED_DIR / "chunks.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    lens = [len(c.text) for c in chunks]
    multi = sum(len(c.sections) > 1 for c in chunks)
    print(f"size={config.CHUNK_SIZE} overlap={config.CHUNK_OVERLAP}: {len(chunks)} chunks -> {out}")
    print(f"chunk length min/median/max: {min(lens)}/{int(st.median(lens))}/{max(lens)}")
    print(f"chunks spanning more than one section: {multi}")


if __name__ == "__main__":
    main()
