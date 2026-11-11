# HANDOFF.md — read this first in a new chat

> **File locations (2026-11-05):** `LEARNING.md` and the project rules now live in `private/` (`private/LEARNING.md`, `private/CLAUDE.md`). The root `CLAUDE.md` is a one-line stub that imports `private/CLAUDE.md`. If a new session does not seem to follow the project rules (teach first, one variable at a time, update LEARNING.md and EXPERIMENTS.md), read `private/CLAUDE.md` yourself first.

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
- **A fresh session has an empty disk** (raw pages, vectors, installed packages are gone). Rebuild with `bash scripts/rebuild_all.sh` (about 6 to 8 minutes; about 2 minutes on the fallback path below). **If sacred-texts.com is blocked (Cloudflare 403), the script falls back to `data_seed/paragraphs.jsonl`** (see the 2026-11-05 note at the end).
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

## Update 2026-10-28 (judge FROZEN, official baseline done)
- Judge frozen (fingerprint 2578221ecdd4). Official working-set baseline: `eval/results/gen_baseline_working_frozen.json`, summary in EXPERIMENTS.md (correctness 0.81 end-to-end / 0.96 ideal; faithfulness 0.92 / 0.82; citation 0.74 / 0.71).
- Round 2 calibration done (owner graded; amended grades in `eval/calibration_grades_round2_amended.md`).
- **Next:** (1) held-out generation run once: `python scripts/run_generation_eval.py --split held-out --confirm-milestone "baseline" --save baseline_heldout` (needs the owner's go-ahead); (2) finish LEARNING.md: "what we saw" in calibration section 6, round 2, fixes 1/1b/1c, the freeze, results; (3) Ragas side-by-side; (4) Phase 2 retrospective; (5) Phase 3.
- Do not change judge instructions without a new calibration (the runner warns if the fingerprint differs).

## Update 2026-10-28 (held-out generation baseline done)
- Held-out generation baseline run once (frozen judge), logged in `eval/heldout_runs.log` and EXPERIMENTS.md. Do NOT rerun except at a milestone with --confirm-milestone. Headline: correctness 0.67 end-to-end / 0.92 ideal; false refusals 3 of 12 / 1 of 12 (over-cautious generator).
- Remaining in Phase 2: Ragas side-by-side (fixed step; the user wants to explain it in interviews), Phase 2 retrospective in LEARNING.md, then Phase 3.

## Update 2026-11-03 (Phase 2 closed)
- **Phase 2 retrospective (final) written** in LEARNING.md. Phase 2 is complete; the Ragas side-by-side moved to Phase 3 (owner's decision), to run alongside the Phase 3 improvements.
- **Next:** start Phase 3, retrieval first (evidence and candidates listed in the retrospective). Teach the concept before building; one change at a time; score the working set each time with the frozen judge; held-out only at milestones with --confirm-milestone. Ask the owner which retrieval change to try first.

## Backup of the private notes (owner's decision, 2026-11-05)
- **Paused:** automatic Drive uploads by Claude (they cost about 80,000 tokens for LEARNING.md and the Drive tools cannot edit file contents). Drive folder "Mahabharata RAG notes (backups)" holds full copies of HANDOFF, EXPERIMENTS and QUESTION_LOG from 2026-11-05; LEARNING.md was saved manually by the owner.
- **Routine now:** keep committing and pushing to the Git branch as usual. **After every push, remind the owner to download the latest notes files that changed in that push** (name them: LEARNING.md, HANDOFF.md, EXPERIMENTS.md, QUESTION_LOG.md) and save them manually. Send the changed files with SendUserFile if it helps.
- The repo is still public (open question: make it private). Only upload to Drive again if the owner asks.

## Update 2026-11-05 (sacred-texts.com blocked; offline fallback added)
- **Problem:** sacred-texts.com returned HTTP 403 (Cloudflare bot check, header `cf-mitigated: challenge`) in a cloud session, so the download failed. The host was on the allowlist; the block is on the site's side. We do not try to get around it.
- **Fix:** the cleaned text is committed at `data_seed/paragraphs.jsonl` (1,306 paragraphs, about 1.5 MB; `data_seed/README.md` explains the origin). `scripts/rebuild_all.sh` now tries the download; if it fails, or fewer than 237 pages are present, it copies the seed into `data/processed/` and continues with chunking and embedding. It prints a line starting `>>> PATH:` saying which path it took. `RAG_SKIP_DOWNLOAD=1` forces the fallback with no request to the website. Raw pages (96 MB) and other generated data are not committed.
- **Checked:** re-ingesting the raw pages gives a file byte-identical to the seed. Fallback from empty `data/` gives 1,306 paragraphs, 1,670 chunks, embeddings (1670, 384). Baseline reproduced: strict phrase hit@5 = 0.67 (16/24), MRR@5 = 0.35; 66 tests pass (9 + 28 + 4 + 18 + 7).
- **Gotcha:** the downloader asks for page 238 expecting a 404 as the end marker; behind the block that request returns 403, which prints a traceback. The script handles it (it checks the 237 pages are present), so the traceback in the log is harmless when pages exist.
- **Next:** Phase 3, retrieval first. Ask the owner which retrieval change to try first; teach the concept before building.

## Update 2026-11-11 (Phase 3, chunking stage: learning the strategies before choosing)
- **Where we are:** Phase 3 chunking stage, **learning phase** (no code written, nothing scored). Strategies learned in detail and logged in `private/LEARNING.md` ("Stage: Chunking"): fixed (baseline), recursive, sentence-based, semantic, structure-aware, plus a section on sentence splitting (pySBD, NLTK, spaCy). **Still to learn in detail (overview only):** parent-child, sentence window (structure-aware done 2026-11-11). **Then:** the owner chooses 2 or 3 to build and compare, one variable at a time, scored on the working set (retrieval metrics first, free; judge only for likely winners). Only a winner joins the main pipeline.
- **Each strategy entry ends with a "Pending to experiment" list** (open items and the experiments to run). Read those first before experimenting.
- **Key findings so far:** (1) the default recursive splitter has no sentence level, so long paragraphs are cut at spaces (9 of 11 chunks mid-sentence on the longest paragraph); the leftover of a big paragraph does not merge with the next. (2) pySBD hides full stops inside a matched quote pair, so a paragraph that opens and closes with `"` comes back as one sentence: 178 of 1,306 paragraphs (rough scan), 177 of them start with a quote; stripping the outer quotes fixed the test paragraph. (3) spaCy's rule-based splitter did not have that problem but cut after "viz."; no splitter fixes source typos. NLTK and spaCy parser mode are untested (NLTK data cannot be downloaded in the cloud environment: host not allowed).
- **Open decisions for the semantic experiment (not made):** splitter, chunks inside or across paragraphs, first breakpoint rule, size limits.
- **Git:** PR #7 merged. Branch `claude/charming-cori-pre3t4` was restarted from `main` and carries `LEARNING.md` and `HANDOFF.md` updates; no PR open (open one only if the owner asks).
- **Phase 3 map:** a one-page overview of the goal, loop and stages is at `private/phase3_map.html`.
