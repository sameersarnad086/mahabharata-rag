# LEARNING.md — my RAG reference

Updated at the end of every meaningful step. Each entry: Concept / What we built / Alternatives / Gotchas.

## Phase 0 — Setup
**Concept:** A reproducible project skeleton: one config file, raw data cached on disk, metadata-first thinking.
**What we built:** `config.py`, `scripts/download_adi_parva.py`, folder layout (see README).
**Alternatives:** Project Gutenberg plain text (one big file, needs splitting by parva); sacred-texts HTML (already split into sections, which gives us section metadata for free).
**Gotchas:**
- Page numbers are offset: `m01001` is the Translator's Preface, `m01002` is Section I, so page = section + 1. Files are named `section_NNN.html` by *page*, so file 237 = Section CCXXXVI. Chunk metadata must use the real Roman-numeral section from the page title, not the file number, or every citation will be off by one.
- sacred-texts.com redirects `www.` to the bare domain; both hosts had to be allowed in the sandbox network policy.
- Raw pages are ~400 KB each (96 MB total) because they're full of site scripts/JSON; the actual text is a small fraction. Phase 1 ingestion must strip this, and the Sanskrit-name spelling in titles is Roman numerals.

## Phase 1 — Ingestion / cleaning (in progress; reviewed on files 001–003 only)
**Concept:** Chunking and embedding only see strings, so anything left in the text gets cut up and embedded. Ingestion turns raw HTML into clean paragraphs *with metadata* before any chunking. RAG quality is capped here: no later stage can fix embedded garbage.
**What we built:** [`src/rag/ingest.py`](src/rag/ingest.py) (`parse_file`) using BeautifulSoup with the stdlib `html.parser` backend; [`scripts/inspect_ingest.py`](scripts/inspect_ingest.py) prints extracted paragraphs and every page-break merge for eyeball review. Raw HTML is never modified.
**Alternatives:** stdlib `html.parser` alone (no dependency, but hand-written state tracking); `lxml` (faster, compiled extra, unnecessary at 237 small files); Project Gutenberg plain text (no HTML, but no per-section structure).
**Gotchas:**
- Raw pages are 99 MB but only 1.4% is story text (1.34 MB). Embedding raw HTML would mean ~124,000 chunks instead of ~1,700, mostly scripts and markup.
- The `<meta description>` / JSON-LD in `<head>` looks like text but is a truncated SEO summary. Never use it.
- Scope extraction to `<article data-slot="reader-content">`; a bare "all `<p>`" also grabs UI text ("No bookmarks yet", copyright footer).
- Read files as UTF-8. Reading as latin-1 turns `'` and `–` into mojibake (`â\x80\x99`), which would corrupt name matching.
- The `SECTION I` heading is in a `<div>`, not the `<h1>`, on file 002; heading detection must not assume `<h1>`.
- Page markers (`p. 16`, Roman `p. xii` in the preface) split paragraphs mid-sentence. Rule (Option A): glue a fragment back if it has the site's `[paragraph continues]` tag, or follows a page marker and starts lowercase. Roughly a third of "paragraphs" on file 003 were fragments before this.
- `printed_page` is approximate (preface numbering goes xii then ix; unclear if a marker means start or end of page). Do not use it in citations yet.
- Closing lines such as "Thus endeth the section called Parva-sangraha…" are kept as text.
- Source typos exist ("sixty-tour"); exact-match retrieval can't rely on clean spelling.
