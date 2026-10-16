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

## Retrieval baseline scores (Phase 1 pipeline, before any change) — 2026-10-14
- **Configuration:** fixed-size chunks 1000/200 characters; `BAAI/bge-small-en-v1.5`, no query prefix; numpy cosine search; 36 labelled questions (`eval/retrieval_questions.csv`), 24 working + 12 held-out; 10 chunks retrieved, scored at k = 1, 3, 5, 10. Code at commit `02a9e84` plus the evaluation code added that day.
- **Two checks:** *section* = chunk touches a gold section (generous); *phrase* = chunk contains an evidence phrase word for word (strict). "No summaries" drops Sections 1, 2 and 95 from the labels (2 working and 1 held-out question have no other gold and are left out).
- **Results at k = 5** (hit = at least one hit in the top 5):

| Set | Check | hit@5 | precision@5 | recall@5 | MRR@5 | nDCG@5 |
|---|---|---|---|---|---|---|
| Working (n=24) | section | 22/24 = 0.92 | 0.30 | 0.65 | 0.58 | 0.32 |
| Working (n=24) | **phrase** | **16/24 = 0.67** | 0.15 | 0.38 | **0.35** | 0.27 |
| Working, no summaries (n=22) | section | 17/22 = 0.77 | 0.25 | 0.64 | 0.54 | 0.29 |
| Working, no summaries (n=22) | **phrase** | **11/22 = 0.50** | 0.11 | 0.33 | **0.28** | 0.25 |
| Held-out (n=12) | section | 10/12 = 0.83 | 0.28 | 0.58 | 0.64 | 0.34 |
| Held-out (n=12) | phrase | 9/12 = 0.75 | 0.17 | 0.48 | 0.58 | 0.44 |
| Held-out, no summaries (n=11) | section | 8/11 = 0.73 | 0.25 | 0.68 | 0.59 | 0.32 |
| Held-out, no summaries (n=11) | phrase | 6/11 = 0.55 | 0.13 | 0.55 | 0.50 | 0.48 |

- **Headline for comparisons in Phase 3:** the strict *phrase* check on the working set, hit@5 and MRR@5, reported with and without the summary sections. **0.67 / 0.35 (0.50 / 0.28 without summaries).** The held-out set is run only at milestones (this baseline is one; both variants were run once and logged in `eval/heldout_runs.log`).
- **Conclusion:** in about a third of questions (half, without the summary passages) the chunk that actually contains the answer is not among the five handed to the model; and only 21% of working questions have it at rank 1. The gap between the section check (0.92) and the phrase check (0.67) says that retrieval usually reaches the right neighbourhood but not the right chunk. Details and per-type reading in `LEARNING.md`.
- **Caveats:** 24 and 12 questions (one working question moves hit rate by 4 points, one held-out question by 8); labels written by Claude and script-checked, not independently verified; set written by Claude (with the owner's approval), so it reflects my idea of what to ask.

## Generation baseline, PROVISIONAL (judge not yet calibrated) — 2026-10-16
- **Configuration:** Phase 1 pipeline unchanged (1000/200 chunks, bge-small, top-5, generator `gemini-3.1-flash-lite`); judge `gemini-3.5-flash`; working set = 24 answerable + 6 unanswerable (the other 2 unanswerable are held-out). Saved: `eval/results/gen_baseline_working.json`. Commit before this entry's code changes: 29001b4.
- **Two modes:** end-to-end (real retrieval) and ideal-context (gold passages handed over, answerable questions only).

| Metric (working set) | End-to-end | Ideal context |
|---|---|---|
| Correctness (refusals count 0) | 0.81 | 0.96 |
| Correctness when it answered | 0.85 | 0.96 |
| Faithfulness | 0.93 | 0.88 |
| Citation support | 0.83 | 0.75 |
| Relevance | 1.00 | 1.00 |
| Gold text among the passages | 0.67 | 1.00 |
| Correct refusals / false refusals | 6/6 / 1/24 | - / 0/24 |

- **Reading (provisional):** handing the model the right passages lifts correctness from 0.81 to 0.96, so most wrong answers come from retrieval, not from the generator. Faithfulness and citation support do not improve in ideal mode (they are slightly lower), so those are generator or judge behaviour, not retrieval. This is exactly what the calibration must test: low faithfulness in ideal mode (e.g. R33 = 0.00, R12 = 0.33) may be real over-claiming or judge strictness.
- **Caveats:** the judge is not calibrated against the owner's grading yet; numbers are not final until it is. Cost of this run about $1.39 (judge, including thinking tokens). Held-out not run.
- **Next:** the owner grades `eval/calibration_sheet.md` blind; compare with `eval/results/calibration_key.json`; fix the judge if agreement is under about 80%.
