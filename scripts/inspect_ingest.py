"""Print what the ingester extracts from a few files, so we can review it by eye.

Usage: python scripts/inspect_ingest.py 1 2      (file numbers)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.ingest import parse_file


def main() -> None:
    for n in map(int, sys.argv[1:]):
        paras = parse_file(config.RAW_DIR / f"section_{n:03d}.html")
        print(f"\n===== file {n:03d}: heading={paras[0].heading!r}, {len(paras)} paragraphs, "
              f"{sum(len(p.text) for p in paras)} chars =====")
        for p in paras:
            if p.merged:
                print(f"  MERGED x{p.merged} [{p.para_index}] ...{p.text[:60]!r} ... {p.text[-60:]!r}")
        for p in paras[:4] + paras[-2:]:
            print(f"[{p.para_index}] sub_parva={p.sub_parva!r} page={p.printed_page}  {p.text[:110]!r}")


if __name__ == "__main__":
    main()
