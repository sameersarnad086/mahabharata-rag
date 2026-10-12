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
