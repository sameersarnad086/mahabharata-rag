# EXPERIMENTS.md

One entry per experiment: date, what changed (ONE variable), why, metrics before → after, conclusion.

_No scored experiments yet; the evaluation harness comes in Phase 2._

## Baseline setup (not yet scored) — 2026-10-12
- **Config:** pure fixed-size chunking, characters, size 1000, overlap 200, chunks may cross paragraph and section boundaries.
- **Why:** simplest possible baseline; structure-aware chunking must beat it. Size is a hypothesis chosen from paragraph stats (median 653, mean 1,021 chars), not yet tested.
- **Output:** 1,670 chunks; length min/median/max 661/1000/1000; 297 chunks (18%) span more than one section.
- **Metrics:** none yet (recall@k, MRR need the Phase 2 test set).
- **Next:** write the question set, then sweep chunk size one value at a time (600, 800, 1000, 1500).

## Baseline embeddings (not yet scored) — 2026-10-13
- **Config:** `BAAI/bge-small-en-v1.5` via sentence-transformers, 384 dims, normalised vectors, query prefix OFF, chunks from the 1000/200 fixed-size baseline.
- **Output:** 1,670 x 384 float32 vectors (2.6 MB), cached in `data/cache/`. Chunk token lengths min/median/max = 165/247/399; 0 chunks over the 512-token limit.
- **Informal check only:** two Bhishma questions returned on-topic chunks, but the best passage was not always ranked first. No metrics until the Phase 2 test set exists.
- **Next experiments (one variable each):** query prefix on/off; other embedding models; chunk-size sweep.

## First end-to-end run, Phase 1 baseline (not yet scored) — 2026-10-13
- **Pipeline:** Ganguli Adi Parva -> 1,306 paragraphs -> 1,670 chunks (fixed-size 1000/200 characters) -> bge-small-en-v1.5 vectors -> numpy cosine top-5 -> Gemini 3.1 Flash-Lite (temperature 0), answer-only-from-passages prompt with `[n]` citations.
- **Informal checks (2 questions):** answerable question gave a supported but incomplete answer with valid citations; unanswerable question was refused correctly. About 1,500 prompt tokens and under 60 output tokens per question.
- **Metrics:** none. Recall@k, MRR, nDCG, faithfulness and answer relevance need the Phase 2 question set.
- **Next:** write the Phase 2 evaluation set (answerable, alias, multi-hop and unanswerable questions), then sweep one variable at a time starting from this baseline.

## Phase 1 closed — 2026-10-13
The configuration in "First end-to-end run" is the **Phase 1 baseline** and the reference for every later comparison. Informal results of 8 questions are in `QUESTION_LOG.md`; the retrospective in `LEARNING.md` lists what to measure first in Phase 2.
