# HANDOFF.md — read this first in a new chat

Short status file so a fresh session (or a fresh chat) can continue without the old conversation.
Update it at the end of every step. Detail lives elsewhere: `CLAUDE.md` (rules), `LEARNING.md` (study notes and decisions),
`EXPERIMENTS.md` (experiment log), `QUESTION_LOG.md` (every question asked, with chunks and verdicts).

## Where we are (2026-10-13, Phase 1 closed)
- **Phase 1 (baseline RAG, no frameworks) is working end to end.** Download, ingest, fixed-size chunks (1000/200 chars), `BAAI/bge-small-en-v1.5` embeddings, numpy cosine top-5, Gemini `gemini-3.1-flash-lite` answers with `[n]` citations.
- **Phase 1 is complete and its final retrospective is written** (`LEARNING.md`, "Phase 1 retrospective (final)"). Nothing is scored yet; everything is informal (8 questions in `QUESTION_LOG.md`). First real numbers come in Phase 2.
- **Git:** branch `claude/vigilant-ride-83azmt`. PR #1 (ingestion) was merged. **PR #2** (chunking, embeddings, retrieval, generation, notes) is open and waits for the user to merge it. After a merge, restart the branch from the updated `main` before new work. Only the user merges.
- **Next steps, in order:** (1) user merges PR #2; (2) plan Phase 2 (details in the retrospective's "What Phase 2 should do"): the user writes 30 to 50 test questions with expected answers and source sections, including alias, multi-hop and unanswerable ones; then build the metrics (recall@k, MRR, nDCG, faithfulness, answer relevance).

## How to work with the user (also in CLAUDE.md)
- The user is **not a coder**. Claude writes all code and explains in plain language: libraries used, how the method works, trade-offs, what results mean. Name every new library.
- **Teach the concept first**, then build. Present options and let the user decide (model choices etc.). Check that tools and models are current before recommending.
- **One variable at a time** when experimenting. Log in `LEARNING.md` and `EXPERIMENTS.md`; each phase ends with a retrospective.
- Don't state guesses as facts (I once wrongly said a new session was needed for an API key). Verify before prescribing.
- Don't open or merge pull requests unless asked. Never paste or print secrets.
- Update this file every few steps and check with the user first (their instruction); don't add it as a per-step rule.

## Environment checklist (lives outside the repo)
- **Secret:** `GEMINI_API_KEY` set as an environment variable in the cloud environment settings (never in files).
- **Network allowlist:** `sacred-texts.com` (source text) and `huggingface.co` (embedding model download) must be allowed. Google's API and PyPI already work.
- **A fresh session has an empty disk** (raw pages, vectors, installed packages are gone). Rebuild with `bash scripts/rebuild_all.sh` (about 6 to 8 minutes).
- Git identity: `sameersarnad086`, `190245750+sameersarnad086@users.noreply.github.com`.

## Map of the code
| Step | Code | Output (gitignored, rebuildable) |
|---|---|---|
| Download | `scripts/download_adi_parva.py` | `data/raw/.../section_001..237.html` |
| Ingest | `src/rag/ingest.py`, `scripts/run_ingest.py`, `scripts/report_ingest.py` | `data/processed/paragraphs.jsonl` (1,306 paragraphs) |
| Chunk | `src/rag/chunking.py`, `scripts/run_chunking.py` | `data/processed/chunks.jsonl` (1,670 chunks) |
| Embed | `src/rag/embedding.py`, `scripts/run_embedding.py` | `data/cache/emb_*.npy` (1,670 x 384) |
| Retrieve | `src/rag/retrieval.py`, `scripts/search.py` | |
| Generate | `src/rag/generation.py`, `scripts/ask.py`, `scripts/list_models.py` | |
| Log a question | `scripts/log_question.py` | appends to `QUESTION_LOG.md` |
| Tests | `tests/test_chunking.py`, `test_retrieval.py`, `test_generation.py` (run each with `python tests/<file>`) | |
All tunables are in `config.py`.

## Key facts to remember
- Section numbers: printed heading (SECTION LXXIV = 74), file name = heading + 1 (`section_075.html`), and the website shows yet another number (unverified). Sections 190 to 199 use non-standard Roman numerals in the source; `section_number` is stored as a plain integer.
- Known weaknesses seen in the baseline: alias problem (Arjuna vs Partha gave an answer vs a refusal), name "Bharata" appears in 255 of 1,670 chunks, multi-hop questions fail, near-duplicate chunks fill top-5 slots, citation check only verifies that a cited number exists (not that it supports the claim).
- The Phase-to-problem map is in `LEARNING.md` ("Known problems: where each one gets solved").
- Prices and model lineups quoted in the notes came from third-party blogs; verify on official pages.

## Open decisions
- Add the page web address to every citation (pending; need the website URL for the page the user sees as "76").
- Compare newer Gemini models (`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash`) in Phase 3; prices unchecked.

## Starter message for a new chat
"Read CLAUDE.md and HANDOFF.md, then LEARNING.md's decisions log. Check git status and the state of the open PR. Rebuild with scripts/rebuild_all.sh if the data folders are empty. Then continue with the next steps in HANDOFF.md."
