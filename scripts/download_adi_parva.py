"""Download Adi Parva (Ganguli translation) from sacred-texts.com, one HTML file per section.

Raw HTML is cached in data/raw/ so we hit the site once. Re-running skips existing files.
Usage: python scripts/download_adi_parva.py [--limit N]
"""
import argparse
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

DELAY_SECONDS = 1.0  # be polite to a volunteer-run site


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=config.NUM_SECTIONS)
    args = ap.parse_args()

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for n in range(1, args.limit + 1):
        out = config.RAW_DIR / f"section_{n:03d}.html"
        if out.exists():
            continue
        url = config.SECTION_URL.format(n=n)
        req = urllib.request.Request(url, headers={"User-Agent": "mahabharata-rag-learning-project"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            out.write_bytes(resp.read())
        print(f"saved section {n:03d}")
        time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()
