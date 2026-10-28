# HANDOFF.md — read this first in a new chat

Short status file so a fresh session (or a fresh chat) can continue without the old conversation.
Update it at the end of every step. Detail lives elsewhere: `CLAUDE.md` (rules), `LEARNING.md` (study notes and decisions),
`EXPERIMENTS.md` (experiment log), `QUESTION_LOG.md` (every question asked, with chunks and verdicts).

## Where we are (2026-10-14, Phase 1 closed, Phase 2 retrieval half done)
- **Phase 1 (baseline RAG, no frameworks) is working end to end.** Download, ingest, fixed-size chunks (1000/200 chars), `BAAI/bge-small-en-v1.5` embeddings, numpy cosine top-5, Gemini `gemini-3.1-flash-lite` answers with `[n]` citations.
- **Phase 1 is complete and its final retrospective is written** (`LEARNING.md`, "Phase 1 retrospective (final)"). Nothing is scored yet; everything is informal (8 questions in `QUESTION_LOG.md`). First real numbers come in Phase 2.
- **Git:** PRs #1, #2 and #3 are all **merged**. The branch `claude/vigilant-ride-83azmt` was restarted from the updated `main` (tip `0c3be73`). Anything committed since is not in `main` until the user asks for a new PR; don't push more commits while a PR is open and unmerged. The user tends to merge within minutes. Only the user merges. Always check a PR's real state with the GitHub tool first.
- **Phase 2 (evaluation) status:** metrics lesson done. **Retrieval question set is complete and labelled:** `eval/retrieval_questions.csv` (36 questions R01-R36; gold sections, evidence phrases, expected answers all filled; checked by `python scripts/verify_labels.py`, ALL PASS) with a **frozen working/held-out split** (24/12, seed 1; `python scripts/make_split.py --check`). Rules in `eval/README.md`. Labels were written by Claude and script-checked, **not independently verified by the user** (the user delegated this). Gold includes the book's summary passages (Sections 1, 2, 95) where they restate answers; the retrospective should score with and without them. **No metric code yet.**
- **Rules for the set:** never read or tune against held-out failures; run held-out only at milestones; don't edit questions/gold to flatter results (after scoring begins, a change needs a logged reason and all earlier runs re-scored); new questions go in a separate file.
- **Retrieval evaluation is built and the baseline is scored** (`scripts/run_retrieval_eval.py`; results in `eval/results/`, `EXPERIMENTS.md`, `LEARNING.md`). Headline (strict phrase check, working set, k=5): hit@5 = 0.67, MRR@5 = 0.35; without summary sections 0.50 / 0.28. Held-out baseline run once (both variants) and logged in `eval/heldout_runs.log` — do not run it again except at a milestone with `--confirm-milestone`.
- **Next steps, in order:** (1) **build the generation evaluation** exactly as planned in `LEARNING.md` ("Phase 2 retrospective (partial)", "Generation evaluation plan"): two modes (end-to-end, ideal context), metrics (faithfulness, citation support, correctness, relevance, refusal accuracy), 36 questions + about 8 unanswerable (verify absence in the corpus first), judge `gemini-3.5-flash` (recommended; the user was asked to reply "go" or change it and had not yet answered), calibrate the judge on about a dozen items, reuse the held-out protection; score the baseline and record it in `EXPERIMENTS.md`; (2) **run Ragas side by side with my own generation metrics (fixed step; the user wants to explain it in interviews; see `LEARNING.md`)**, then finalise the Phase 2 retrospective; (3) Phase 3: start from the hypotheses listed there, one change at a time, scoring working set after each change.
- **The user asked to keep answers short (context was nearly full).** The user is not a coder: explain in plain language, name files not code.
- **Open:** whether the user adds questions of their own (separate file).

## Update 2026-10-16: generation evaluation is BUILT; blocked on a paid key, then needs a trial
- **Built and pushed (tip `29001b4`):** `src/rag/judge.py` (4 judge jobs, JSON replies, checked), `src/rag/eval_generation.py` (scoring logic, ideal-context passages, refusal and citation handling, summaries), `src/rag/evalcache.py` (disk cache so reruns are free and crashed runs resume), `scripts/run_generation_eval.py` (modes, working/held-out protection, `--ids`, `--save`), `scripts/verify_unanswerable.py`, `eval/generation_questions.csv` (8 unanswerable questions G01-G08, absence scan-checked; **not yet reviewed by the user**), `tests/test_eval_generation.py` (28 pass; all other test files pass). The lesson is in `LEARNING.md` ("Generation evaluation: what it is and how it runs").
- **Judge:** `gemini-3.5-flash` (user approved; available to the key). Prices (unofficial) $1.50 in / $9.00 out per million tokens; thinking tokens bill as output and run several times the visible output. Rough estimate $3 to $5 per full run, uncertain.
- **Blocker found:** the key was on the free tier, allowing 20 requests/day for the judge model (429). The user then set a PAID key in the environment variable `GEMINI_API_KEY`; it only reaches a NEW session. Gemini 503 "high demand" errors are common; the runner waits longer (`EVAL_RETRY_WAITS`) and caches.
- **Not yet seen:** no question has been fully scored end to end. The first complete record (R01, R03) is the trial: `python scripts/run_generation_eval.py --ids R01,R03 --mode end-to-end`. Check the judge's JSON, verdicts, token use and cost before anything bigger.
- **Next, in order:** trial and review with the user; user reviews G01-G08; user hand-grades about 12 answers to calibrate the judge (agree under about 80% means fix the judge instructions first); baseline run on the working set, both modes; held-out run once with `--confirm-milestone`; record in `EXPERIMENTS.md` and `LEARNING.md`; run Ragas side by side with our metrics (fixed step); finalise the Phase 2 retrospective; then Phase 3.
- **Git:** PR #4 merged. This branch has no open PR; it is ahead of `main` with the Ragas note, the lesson and the build. Open a PR only if the user asks.

## How to work with the user (also in CLAUDE.md)
- The user is **not a coder**. Claude writes all code and explains in plain language: libraries used, how the method works, trade-offs, what results mean. Name every new library.
- **Teach the concept first**, then build. Present options and let the user decide (model choices etc.). Check that tools and models are current before recommending.
- **One variable at a time** when experimenting. Log in `LEARNING.md` and `EXPERIMENTS.md`; each phase ends with a retrospective.
- Don't state guesses as facts (I once wrongly said a new session was needed for an API key). Verify before prescribing.
- Don't open or merge pull requests unless asked. Never paste or print secrets.
- **Before saying anything about a pull request, check its real state with the GitHub tool** (merged? which commits?). I got this wrong twice by assuming.
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
- **The central challenge is the lineage and one person with more than one name problem** (defined in `LEARNING.md`, "Named problems"). Seen in the baseline: Arjuna vs Partha gave an answer vs a refusal; name "Bharata" appears in 255 of 1,670 chunks, multi-hop questions fail, near-duplicate chunks fill top-5 slots, citation check only verifies that a cited number exists (not that it supports the claim).
- The Phase-to-problem map is in `LEARNING.md` ("Known problems: where each one gets solved").
- Prices and model lineups quoted in the notes came from third-party blogs; verify on official pages.

## Open decisions
- Add the page web address to every citation (pending; need the website URL for the page the user sees as "76").
- Compare newer Gemini models (`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash`) in Phase 3; prices unchecked.

## Starter message for a new chat
"Read CLAUDE.md and HANDOFF.md, then LEARNING.md's decisions log. Check git status and the state of the open PR. Rebuild with scripts/rebuild_all.sh if the data folders are empty. Then continue with the next steps in HANDOFF.md."

## Update 2026-10-16 (generation eval run)
- Paid Gemini key works. Trial R01/R03 fine. **Provisional baseline** (working set, both modes) is in `EXPERIMENTS.md` and `eval/results/gen_baseline_working.json`; judge NOT yet calibrated.
- **Waiting on the user:** grade `eval/calibration_sheet.md` (12 items, blind). Do not open or show `eval/results/calibration_key.json` (judge's scores) before they finish. Then compare, fix judge if agreement < ~80%, freeze judge prompt, re-score.
- Unanswerable split: 6 working + 2 held-out. Held-out generation run still not done (needs --confirm-milestone). `scripts/rebuild_all.sh` pipe bug fixed.

## Update 2026-10-28 (judge fixes done; waiting on round 2)
- Judge fixes applied: 1 (names), 1b (passages only), 1c (spelling variants). Only the "Names" rule in `src/rag/judge.py` changed; correctness rubric untouched. Amended owner grades in `eval/calibration_grades_amended.md`; blind originals in `eval/calibration_grades.md`.
- Agreement on round 1 items with amended grades: correctness 92%, all-supported 89%, citations 100% (consistency check only).
- **Waiting on the user:** grade round 2 (8 fresh items) in the form https://claude.ai/artifact/TsUJZgtkcGusgWpMBPKEQu (older duplicate link: .../5xJNJ4uYqHPmbdw8s61ssr). Key with judge scores (do not show before grading): `eval/results/calibration_key_round2.json`.
- Then: compare with `scripts/compare_calibration.py` (needs a run that includes the 8 round-2 ids re-scored with the current judge: run `run_generation_eval.py --ids ... --save calib_round2`), freeze judge if about 80% or more, rerun the official baseline (both modes), then held-out once with --confirm-milestone.
- Dev tooling: Graphify and claude-mem configured via `.claude/hooks/session-start.sh` (cloud only).
