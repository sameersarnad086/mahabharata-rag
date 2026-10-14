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
| `approx_sections` | my original guess of where the answer is (kept for the record; `gold_sections` is the truth) |
| `gold_sections` | sections that state the answer, found by reading the text (printed heading numbers, not file numbers). Includes the book's summary passages (Sections 1, 2 and 95) where they restate the answer, so a correct summary chunk is not scored as a miss |
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

## How the labels were made, and what they are not
- Written by Claude from reading the text, then checked by `python scripts/verify_labels.py`: every evidence phrase must appear word for word in a gold section and sit fully inside at least one chunk. **They have not been independently checked by the project owner**, so a wrong or missing label is possible; any error found later must be handled under rule 3.
- A chunk counts as a hit if its section is gold (section check) and, more strictly, if it contains any one of the evidence phrases (phrase check).
- Identical labels were given to both halves of each name pair, so the pair is a fair test of the name problem.
