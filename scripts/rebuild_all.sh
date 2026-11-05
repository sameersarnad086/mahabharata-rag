#!/usr/bin/env bash
# Rebuild everything derived from the committed code, in a fresh session (empty disk).
# Takes roughly 6-8 minutes: ~4 min polite downloading, ~1.5 min embedding.
# Needs network access to huggingface.co (embedding model), and to sacred-texts.com for the download path.
# If the download fails (e.g. the site's Cloudflare bot check returns 403) or pages are missing, it falls back to
# the committed cleaned text data_seed/paragraphs.jsonl and skips download + ingest.
# Usage: bash scripts/rebuild_all.sh
#        RAG_SKIP_DOWNLOAD=1 bash scripts/rebuild_all.sh   # force the fallback, no request to the website
set -euo pipefail
cd "$(dirname "$0")/.."

pip install -q -r requirements.txt
PAGES_DIR=data/raw/mahabharata/adi_parva
have_pages() { [ "$(ls "$PAGES_DIR"/section_*.html 2>/dev/null | wc -l)" -ge 237 ]; }

PATH_TAKEN=""
if [ "${RAG_SKIP_DOWNLOAD:-0}" != "1" ] && { python3 scripts/download_adi_parva.py || have_pages; } && have_pages; then
  PATH_TAKEN="download"
  echo ">>> PATH: download path (237 raw pages present) -> ingest from the raw pages"
  python3 scripts/run_ingest.py $(seq 1 237)           # -> data/processed/paragraphs.jsonl
  python3 scripts/report_ingest.py > /dev/null         # sanity check (no pipe to head: it broke the script under set -e)
else
  PATH_TAKEN="seed"
  echo ">>> PATH: FALLBACK -> using committed data_seed/paragraphs.jsonl (download skipped, failed or incomplete)"
  mkdir -p data/processed
  cp data_seed/paragraphs.jsonl data/processed/paragraphs.jsonl
fi
echo ">>> paragraphs: $(wc -l < data/processed/paragraphs.jsonl) (expected 1306), path taken: $PATH_TAKEN"
python3 scripts/run_chunking.py                          # -> data/processed/chunks.jsonl
python3 scripts/run_embedding.py                         # -> data/cache/emb_*.npy
echo "Rebuild done. Try: python scripts/search.py \"Who was Shakuntala's son?\""
