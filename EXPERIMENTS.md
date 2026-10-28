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

## Judge calibration, round 1 (owner's blind grades vs judge) — 2026-10-21
- **What:** owner graded 12 end-to-end answers blind (`eval/calibration_grades.md`, verbatim); compared with the judge's scores (`eval/results/calibration_key.json`). Judge prompts unchanged so far.
- **Agreement:** correctness 8/12 exact (67%); "all sentences supported" 8/9 scored items; citation backing per sentence 11/14 (79%). Below the 80% bar on correctness, borderline on citations. Tiny sample, read as a signal about failure types, not a precise rate.
- **Disagreements and likely cause:**
  - R08 and R20 citations: judge said "not backed" because the passage says "the king" / "the Rishi, Vyasa" while the answer uses the question's name (Parikshit / Dwaipayana). Judge is too literal about names; this is the many-names-for-one-person problem hitting the judge. Owner marked both as backed.
  - R12 faithfulness: judge marked both claims unsupported (no evidence quoted), yet its citation check on the same passage said the passage "explicitly states" it. Judge is inconsistent with itself here; claim wording ("the five brothers set the house on fire" vs the passage's "Bhima set fire") may be the trigger. Needs a closer look.
  - Correctness: R08 judge 0.5 (wanted the curse as well), owner yes; R05 judge 0, owner partly; R12 judge 0.5, owner no; R25 (refusal) not scored by the judge, owner partly. No consistent direction: judge stricter on two, more lenient on one.
  - R21 sentence 3 (marriage claim not in passage): owner and judge agree it is unsupported.
- **Owner's retrieval observations (kept for Phase 3):** R25 top-1 chunk (Section 66) is irrelevant; R05, R08, R12 the key paragraphs sit in neighbouring chunks and were missed; several items show right section but wrong paragraph; the owner asks what drives retrieval (it is embedding similarity of the question to chunk text). R20 and R01: chunk boundaries cut off context. Generation judged fine apart from R21 sentence 3.
- **Open decision:** fix the judge before trusting scores. Candidate changes, one at a time: (1) tell the citation and claim judges that names, epithets and titles of the same person may differ and to accept them when the passage context makes the identity clear; (2) require evidence quotes for "unsupported" verdicts, then re-check R12; (3) clarify correctness rubric for partial answers.

## Judge fix 1 of 3: name handling — 2026-10-21
- **Change (one variable):** added a "Names" rule to the claim-verification and citation prompts in `src/rag/judge.py` (different names, titles and epithets of the same person match when the passage makes identity clear or the alias is well known; two different people sharing a name must not be merged). Nothing else changed. Re-scored the same 12 cached answers (`eval/results/gen_calib_fix1.json`, $0.35); comparison by `scripts/compare_calibration.py`.
- **Result vs owner's grades:**

| Measure | Before | After |
|---|---|---|
| Correctness | 8/12 = 67% | 8/12 = 67% (not touched by this fix) |
| All sentences supported (per answer) | 8/9 = 89% | 7/9 = 78% |
| Citation backing (per sentence) | 11/14 = 79% | 13/14 = 93% |

- **Conclusion:** the fix did what it was meant to: R08 and R20 citations are now judged backed (the judge's reason for R20 now reads "the Rishi (Vyasa/Dwaipayana)"). Side effect: R10 faithfulness dropped to 0.75 because the judge now rejects the claim "the vow was taken so that no children of his own could claim the throne" as not stated in the passage (the owner marked it supported). This looks like ordinary judge variance or strictness, not the names rule, and is a candidate for fix 2/3 discussion.
- **Still open:** correctness (R25, R05, R08, R12 disagree) and R12 faithfulness ("the five brothers" vs the passage's "sons of Pandu" / "Bhima set fire").

### Note on R10 and amended grades — 2026-10-21
After seeing the judge's reason, the owner agreed the judge was right on R10 sentence 3 (the passage states the celibacy vow, not that its purpose was to exclude his own children; the sentence is true in the story but goes beyond the passage). Recorded as an amendment in `eval/calibration_grades_amended.md`; the blind originals stay untouched. With the amended grades: before fix 1 correctness 67% / all-supported 78% / citations 86%; after fix 1 correctness 67% / all-supported 89% / citations 100%. Caution: a grade revised after seeing the judge is not independent evidence, which is one reason for the planned second round of fresh blind grading.

### Correctness rule settled with the owner; round 2 prepared — 2026-10-21
- **Owner's rule for correctness (matches the judge's existing rubric, so no judge change):** full = the key facts of the expected answer including the cause when the expected answer has one (R08: the curse is needed, "bitten by Takshaka" alone is partly); partly = right idea or right entity but a key part missing or hedged (R05, R12); no = wrong, or a refusal on an answerable question (R25).
- **Amendments** to the owner's R25 (partly→no), R08 (yes→partly), R12 (no→partly), R10 (see above) are in `eval/calibration_grades_amended.md`; blind originals untouched. With them, after judge fix 1: correctness 11/12 = 92%, all-supported 8/9 = 89%, citations 14/14 = 100%. Caution: these grades were revised after seeing the judge, so this is a consistency check, not independent evidence.
- **Remaining disagreements:** R05 correctness (owner partly, judge 0: the answer named Agni as burning the forest but said the passages do not say who set it) and R12 faithfulness (judge rejects "the five brothers" claims; the passage says "sons of Pandu" and "Bhima").
- **Round 2 (fresh, blind):** 8 answers not used in round 1, chosen by fixed rules in `scripts/pick_round2.py`: R26, R31, R34, R36 (judge-flagged), R11, R13 (clean), G04 (refusal), R14. Form: `eval/calibration_form_round2.html`. This is the real test of the frozen judge.

## Judge fix 1b: name rule restricted to the passages (owner's decision) — 2026-10-21
- **Change (one variable):** the "Names" rule no longer lets the judge use its own knowledge of aliases; two names match only if the passages show it. Same 12 cached answers re-scored (`eval/results/gen_calib_fix1b.json`, $0.35). Compared with the amended owner grades.
- **Result:** correctness 11/12 = 92%; all-supported 7/9 = 78%; citations 11/14 = 79% (fix 1 with outside-knowledge aliases: 92% / 89% / 100%).
- **What changed:** R08 ("the king" vs Parikshit) and R20 (Vyasa vs Dwaipayana) citations are flagged again, as the owner expected: the passages do not show those identities, so this is a retrieval gap to fix in Phase 3, not a generator fault. New side effect: R21's first citation is now flagged because the passage spells the name "Hidimva" and the answer "Hidimba". That is a spelling variant, not outside knowledge, so the rule probably should let spelling variants match (proposed fix 1c, not applied).
- **Judge variance noted:** R10 faithfulness was 1.0 (baseline), 0.75 (fix 1), 1.0 (fix 1b) on the same answer at temperature 0. Changing the prompt text moves borderline verdicts, so single-item flips of this kind are noise; per-item comparisons need several items to mean anything.
- **Under the passages-only standard** the owner's own R08 and R20 citation grades (given using knowledge of the aliases) would become "no"; not yet amended, awaiting the owner's confirmation.

## Judge fix 1c: spelling variants match; R08/R20 grades amended — 2026-10-28
- **Change (one variable):** added to the "Names" rule in `src/rag/judge.py`: different spellings of the same name (Hidimba/Hidimva, Yudhishthira/Yudhisthira) always match; different names still need the passages to link them. Re-scored the same 12 cached answers (`eval/results/gen_calib_fix1c.json`, $0.36).
- **Owner grade amendment:** R08 and R20 citation grades yes→no in `eval/calibration_grades_amended.md` (blind originals untouched). Reason: the cited passages say "the king" / "Vyasa" and never name Parikshit / Dwaipayana; under the passages-only standard they are not backed. For R08 the nearby "Parikshita" in the passage is the son (a different person), so the judge's flag is also correct, and it is a worked example of the same-name-different-people trap for Phase 3.
- **Result vs amended owner grades:** correctness 11/12 = 92%; all-supported 8/9 = 89%; citations 14/14 = 100%.

| Judge version | Correctness | All supported | Citations |
|---|---|---|---|
| Original | 67% | 89% | 79% |
| Fix 1 (alias knowledge) | 67% | 78% | 93% |
| Fix 1b (passages only) | 92% | 78% | 79% |
| **Fix 1c (+ spelling variants), amended grades** | **92%** | **89%** | **100%** |

- **Still disagreeing:** R05 correctness (owner partly, judge 0) and R12 faithfulness (judge rejects "the five brothers" claims). Not changed, to avoid tuning the judge to single items.
- **Caution:** amended grades were revised after seeing the judge, so this is a consistency check, not independent evidence. Round 2 (8 fresh blind answers) is the independent test. If agreement on round 2 is about 80% or more, the judge instructions are frozen.

## Judge calibration, round 2 (8 fresh blind answers, judge fix 1c, not tuned on these) — 2026-10-28
- **Setup:** owner graded 8 answers not used in round 1 (`eval/calibration_grades_round2.md`, Item 1 citations left as "?" and excluded). Judge = current instructions (fix 1c), scores in `eval/results/gen_calib_round2.json` ($0.23). Compared with `scripts/compare_calibration.py`.
- **Agreement:** correctness 5/8 = 62%; all-supported 6/7 = 86%; citations 11/13 = 85%. If correctness is reduced to "acceptable (yes or partly) vs wrong (no)": round 2 8/8, round 1 11/12, together 19/20 = 95%.
- **Disagreements (no judge change made):**
  - Correctness, the "what is the key fact" boundary, mixed direction: R13 and R14 (owner partly: missed the Yadava girl and the chariot; judge 1.0, "forcible seizure" is the key fact); R34 (owner yes; judge 0.5 for omitting that he composed the Mahabharata).
  - Citation strictness on minor descriptors: R36 (judge: passage does not say Janamejaya was a "monarch"), R11 (judge: passage does not say Parikshit was "king"). Owner marked both backed.
  - R31 faithfulness: owner Supported=no; judge faithfulness 1.0 because passage 5 names Astika and his birth to the snakes' sister. The citation check (only passage [3], which does not name Astika) marked both sentences not backed, agreeing with the owner. The judge is arguably right on both: the claim holds across the five passages, but the cited passage [3] alone does not back it.
- **Conclusion:** the judge generalises on supported and citations (above 80%, small samples: 7 and 13 items). Correctness on the 3-level scale is below 80% mainly because expected answers hold several facts and "key fact" is a judgement call; the coarse correct vs wrong view agrees 95%. Round 2 was the untouched test, so tuning the judge on these items now would remove its independence. Decision recorded below.

## Judge frozen; OFFICIAL generation baseline, working set — 2026-10-28
- **Judge frozen** at fingerprint `2578221ecdd4` (`JUDGE_FROZEN_FINGERPRINT` in `config.py`; every run records its own fingerprint and warns if it differs). Evidence: round 1 with amended grades, correctness 92%, all-supported 89%, citations 100%; round 2 (fresh, blind, with owner amendments R13/R14/R31) correctness 88%, all-supported 100%, citations 85%. Known limits: citation check is strict on minor descriptors (R36 "monarch", R11 "King"); "key fact" in partially answered questions is a judgement call (R34); R05 correctness (owner partly, judge 0) and R12 faithfulness unresolved. Amended grades: `eval/calibration_grades_amended.md`, `eval/calibration_grades_round2_amended.md`; blind originals untouched. Owner: the answers are reasonably good from an end-user view.
- **Run:** `python scripts/run_generation_eval.py --mode both --save baseline_working_frozen` → `eval/results/gen_baseline_working_frozen.json` (24 answerable + 6 unanswerable end-to-end; 24 ideal context; $1.57). Generator answers were reused from the cache (same prompts), so only the judge scores changed.

| Metric (working set) | End-to-end | Ideal context |
|---|---|---|
| Correctness (refusals count 0) | 0.81 | 0.96 |
| Faithfulness | 0.92 | 0.82 |
| Citation support | 0.74 | 0.71 |
| Relevance | 1.00 | 1.00 |
| Gold text in the passages | 0.67 | 1.00 |
| Correct refusals / false refusals | 6/6 / 1/24 | n/a |

- **Versus the provisional baseline:** correctness and relevance identical; faithfulness 0.93→0.92 and 0.88→0.82; citation support 0.83→0.74 and 0.75→0.71. The citation drop is the passages-only name rule at work (R08, R20 style cases are now flagged), which the owner chose.
- **Conclusion:** this is the reference for all Phase 3 comparisons. Retrieval is still the main weakness (correctness 0.81 → 0.96 with the gold passages). Held-out not run yet (needs `--confirm-milestone`).

## Held-out generation baseline (frozen judge) — 2026-10-28
- **Run once** with `--split held-out --confirm-milestone "baseline generation evaluation, frozen judge 2578221ecdd4"` → `eval/results/gen_baseline_heldout.json` (aggregates only, by design), logged in `eval/heldout_runs.log`. 12 answerable + 2 unanswerable end-to-end, 12 in ideal context. Judge $0.61. Per-question failures were deliberately not inspected (held-out rule).

| Metric | Held-out end-to-end | Held-out ideal | Working end-to-end | Working ideal |
|---|---|---|---|---|
| Correctness (refusals count 0) | 0.67 | 0.92 | 0.81 | 0.96 |
| Correctness when it answered | 0.89 | 1.00 | 0.85 | 0.96 |
| Faithfulness | 0.89 | 0.97 | 0.92 | 0.82 |
| Citation support | 0.85 | 0.86 | 0.74 | 0.71 |
| Relevance | 1.00 | 1.00 | 1.00 | 1.00 |
| Gold text in the passages | 0.75 | 1.00 | 0.67 | 1.00 |
| Correct / false refusals | 2 of 2 / 3 of 12 | n/a / 1 of 12 | 6 of 6 / 1 of 24 | n/a / 0 of 24 |

- **Reading:** answers that are given are good (correctness when answered 0.89 end-to-end, 1.00 ideal; faithfulness 0.89 to 0.97). The lower headline correctness comes from **false refusals: 3 of 12 end-to-end** (2 caused by retrieval, 1 by generation) and **1 of 12 even with the gold passages** (a generation-caused refusal). On the working set it was 1 of 24 and 0 of 24. Retrieval was no worse than on the working set (gold in passages 0.75 against 0.67), so the gap is over-cautious refusing, not retrieval.
- **Does the working set generalise?** Directionally yes for retrieval-limited correctness (ideal context is clearly higher than end-to-end in both sets) and for refusal behaviour on unanswerable questions (2 of 2). The faithfulness pattern did not repeat (ideal context was higher here, lower on the working set), so the working-set faithfulness dip is probably question-specific, not a general effect. With 12 questions one question is 8 points, so none of these differences is conclusive.
- **Next:** do not tune on held-out failures. The false-refusal rate is a candidate for the Phase 3 "generation / I don't know handling" stage, to be examined on the working set.
