# data_seed

`paragraphs.jsonl` is the **cleaned text of the Adi Parva** from Kisari Mohan Ganguli's English translation of the
Mahabharata (public domain), derived from the pages on sacred-texts.com.

- 1,306 paragraphs, one JSON object per line, each with its source file, section heading, sub-parva, paragraph index,
  printed page and `section_number` (the metadata every chunk and citation depends on).
- **How it was produced:** `scripts/download_adi_parva.py` fetched the 237 section pages, then
  `scripts/run_ingest.py $(seq 1 237)` (code in `src/rag/ingest.py`) stripped the web page down to story paragraphs
  and glued back sentences split by printed-page breaks.
- **Why it is committed:** sacred-texts.com can block automated downloads (a Cloudflare bot check returned HTTP 403 in
  a cloud session). With this file, `scripts/rebuild_all.sh` falls back to it and a fresh session never depends on the
  website. The raw pages (about 96 MB) and all other generated data are deliberately not in the repo.
