#!/usr/bin/env bash
# Rebuild everything derived from the committed code, in a fresh session (empty disk).
# Takes roughly 6-8 minutes: ~4 min polite downloading, ~1.5 min embedding.
# Needs network access to sacred-texts.com and huggingface.co (environment network settings).
# Usage: bash scripts/rebuild_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

pip install -q -r requirements.txt
python3 scripts/download_adi_parva.py                    # skips pages it already has
python3 scripts/run_ingest.py $(seq 1 237)               # -> data/processed/paragraphs.jsonl
python3 scripts/report_ingest.py | head -8               # sanity check
python3 scripts/run_chunking.py                          # -> data/processed/chunks.jsonl
python3 scripts/run_embedding.py                         # -> data/cache/emb_*.npy
echo "Rebuild done. Try: python scripts/search.py \"Who was Shakuntala's son?\""
