# EXPERIMENTS.md

One entry per experiment: date, what changed (ONE variable), why, metrics before → after, conclusion.

_No scored experiments yet; the evaluation harness comes in Phase 2._

## Baseline setup (not yet scored) — 2026-10-12
- **Config:** pure fixed-size chunking, characters, size 1000, overlap 200, chunks may cross paragraph and section boundaries.
- **Why:** simplest possible baseline; structure-aware chunking must beat it. Size is a hypothesis chosen from paragraph stats (median 653, mean 1,021 chars), not yet tested.
- **Output:** 1,670 chunks; length min/median/max 661/1000/1000; 297 chunks (18%) span more than one section.
- **Metrics:** none yet (recall@k, MRR need the Phase 2 test set).
- **Next:** write the question set, then sweep chunk size one value at a time (600, 800, 1000, 1500).
