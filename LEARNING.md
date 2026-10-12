# LEARNING.md — my RAG reference

Updated at the end of every meaningful step. Each entry: Concept / What we built / Alternatives / Gotchas.

## Phase 0 — Setup
**Concept:** A reproducible project skeleton: one config file, raw data cached on disk, metadata-first thinking.
**What we built:** `config.py`, `scripts/download_adi_parva.py`, folder layout (see README).
**Alternatives:** Project Gutenberg plain text (one big file, needs splitting by parva); sacred-texts HTML (already split into sections, which gives us section metadata for free).
**Gotchas:** (to fill in after the download)
