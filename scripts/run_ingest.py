"""Run the ingester on chosen files and save the clean paragraphs for review.

Writes two files next to --out:
  <out>.jsonl  one JSON object per paragraph (what later stages will read)
  <out>.txt    human-readable version to open and eyeball
Usage: python scripts/run_ingest.py 1 2 3 --out samples/ingest_sample
"""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.ingest import parse_file


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", type=int, nargs="+")
    ap.add_argument("--out", default=str(config.PROCESSED_DIR / "paragraphs"))
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(out.with_suffix(".jsonl"), "w", encoding="utf-8") as jl, \
         open(out.with_suffix(".txt"), "w", encoding="utf-8") as tx:
        for n in args.files:
            paras = parse_file(config.RAW_DIR / f"section_{n:03d}.html")
            tx.write(f"\n{'=' * 70}\nfile {n:03d} | {paras[0].heading} | {len(paras)} paragraphs\n{'=' * 70}\n")
            for p in paras:
                jl.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
                tag = f"[{p.para_index}] page~{p.printed_page} sub_parva={p.sub_parva}"
                if p.merged:
                    tag += f" (merged x{p.merged})"
                tx.write(f"\n{tag}\n{p.text}\n")
            total += len(paras)
    print(f"wrote {total} paragraphs -> {out.with_suffix('.jsonl')} and .txt")


if __name__ == "__main__":
    main()
