# eval/ — the evaluation sets

`retrieval_questions.csv` is the question set for the **retrieval** evaluation (did the right passages reach the model?).
A separate generation set (including unanswerable questions) comes later.

## Columns
| Column | Meaning |
|---|---|
| `id` | R01 to R36 |
| `unit` | questions that share a unit are the same fact asked with different names; they always stay in the same split |
| `type` | plain, paraphrase, alias, spelling, lineage, multihop, ambiguous |
| `band`, `anchor_section` | rough place in the book (early = Sections 1-79, middle = 80-158, late = 159-236); a best guess, used only to spread the questions evenly |
| `approx_sections` | where I expect the answer to be; **a guess until `gold_sections` is filled** |
| `gold_sections` | sections verified from the text to contain the answer (printed heading numbers, not file numbers) |
| `evidence_phrases` | short exact phrases copied from those passages |
| `expected_answer` | the short correct answer, checked against the text |
| `split` | `working` (used during experiments) or `held-out` (only at milestones) |
| `status`, `notes` | where the question is in its checking |

## Rules
1. **The split is frozen.** It was drawn once with a fixed rule (see `split_info.json` and `scripts/make_split.py`) before any question was scored. `python scripts/make_split.py --check` verifies it.
2. **Never read or tune against held-out failures.** Run the held-out set at milestones only (baseline, end of a phase).
3. **Do not edit questions or gold labels to flatter a result.** Fixing a label before scoring begins is fine. After scoring has begun, any change needs a logged reason and every earlier run must be re-scored with the new labels.
4. **New questions go in a separate, clearly marked file** (not in this one).
5. Q1 to Q8 in `QUESTION_LOG.md` are exploration notes, not part of this set.
