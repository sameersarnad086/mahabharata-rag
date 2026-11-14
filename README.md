# Mahabharata RAG

An experimental retrieval-augmented generation (RAG) system over one of the hardest public-domain texts there is: the *Mahabharata* (Kisari Mohan Ganguli's English translation, starting with the Adi Parva). The project measures what actually makes RAG work on complex, translated, genealogy-heavy literature, and builds towards a lineage and story explorer for the Solar (Suryavamsha) and Lunar (Chandravamsha) dynasties.

## Why this corpus

Most RAG demos run on clean modern prose. This corpus breaks the usual assumptions:

- **One person, many names.** Arjuna is also Partha, Dhananjaya, Phalguna; Krishna is Vasudeva, Keshava, Madhava. Spellings vary (Hidimba / Hidimva, Vyasa / Dwaipayana).
- **One name, many people.** Several Parikshits and Janamejayas across generations.
- **Facts spread across chapters.** "How are Krishna (Yadu line) and Arjuna (Puru line) related?" has no single answering passage; it is a multi-hop question through Yayati.
- **Nineteenth-century translated prose.** Long compound sentences, semicolon-joined lists, speeches wrapped in quotation marks that run across paragraphs, and old transliteration. General-purpose text-processing tools are not built for this.
- **Sources disagree.** Different texts give different lineage lists; the system should report the disagreement with citations, not silently pick one.

## Goal

1. **A lineage and story explorer.** A knowledge graph of people and relationships (father, mother, son, spouse, descendant-of), every edge carrying its source citation, combined with RAG over the texts for the story around each person and event. It should answer graph questions (ancestors, descendants, paths between two people, common ancestors) and show an interactive family tree with citations on every link, handling name ambiguity and conflicting sources explicitly.
2. **Reusable building blocks for literary and narrative corpora**, packaged separately from the Mahabharata so others can use them (see [Reusable components](#reusable-components)). The full proposal is in [`docs/literary-text-processing-proposal.md`](docs/literary-text-processing-proposal.md).

## What is being tested

The work is run as a series of controlled experiments, one change at a time, each scored against the same frozen yardstick:

1. **Where does a RAG system fail, retrieval or generation?** (Answered: retrieval.)
2. **Does how the text is segmented change what gets retrieved?** Seven chunking strategies are being compared: fixed-size, recursive, sentence-based, semantic, structure-aware, parent-child and sentence-window.
3. **Do general-purpose sentence splitters hold up on translated epic prose?** (Partly: see results.)
4. **Can embedding similarity detect narrative continuity?** For example, "These eight are known as the Vasus." and "Of these, Dhara and the truth-knowing Dhruva were born of Dhumra." belong together even though their similarity score is low.
5. **Does entity- and alias-aware processing fix the "Arjuna / Partha" failures?**
6. **Can a knowledge graph plus RAG answer multi-hop lineage questions** that no single passage answers?

## Method

- **Baseline first, no frameworks.** Fixed-size chunks (1,000 characters, 200 overlap), `BAAI/bge-small-en-v1.5` embeddings, brute-force cosine search over NumPy, answers from Gemini with `[n]` citations. No vector database or RAG framework until the comparison phase.
- **An evaluation harness before any tuning.** 36 labelled retrieval questions plus 8 unanswerable ones, with a frozen split (24 working, 12 held-out) and the held-out set locked behind an explicit flag. Retrieval metrics (hit@k, MRR, nDCG, with a strict evidence-phrase check and a looser section check) and an LLM-as-judge for correctness, faithfulness, citation support and refusals.
- **Retrieval and generation scored separately,** in two modes: end-to-end, and with the correct passages supplied ("ideal context"), so a retrieval failure cannot hide as a generation failure.
- **A calibrated, frozen judge.** The judge was checked against human grades in two rounds, then frozen with a fingerprint so later comparisons cannot silently change the ruler.
- **Criteria written down before running.** Gates, scores and the winner rule for each comparison are recorded in the notes before the experiment is run.
- **Everything cached and reproducible.** Embeddings and model replies are cached to disk; a fresh checkout rebuilds from a committed copy of the cleaned corpus if the source website blocks automated downloads.

## Results so far

**Baseline** (Phase 1 pipeline, nothing tuned):

| | Working set (24 questions) | Held-out (12 questions) |
|---|---|---|
| Correct passage in the top 5 (strict check) | 0.67 | 0.75 |
| Answer correctness, end-to-end | 0.81 | 0.67 |
| Answer correctness, correct passages supplied | 0.96 | 0.92 |

With the right passages the model is right about 92-96% of the time; with what the system actually retrieves it is not. **Retrieval, not generation, is the bottleneck.** Every unanswerable question (8 of 8) was correctly refused.

**Sentence segmentation on the corpus** (five candidates plus a control, all 1,306 paragraphs, hand-checked boundaries):

- About **71% of the text sits in paragraphs over 1,000 characters**, so any strategy that keeps paragraphs whole still has to split most of the corpus, and needs reliable sentence boundaries.
- The default rule-based splitter (pySBD) **left 21% of the long paragraphs as a single "sentence"**, because it treats a quote-wrapped speech as one unbreakable unit.
- A rule-based splitter built on spaCy with four targeted fixes (an abbreviation merge for "viz.", "i.e.", "Mr." and similar, a lowercase merge for stray full stops, and opening and closing quote placement) passes all 13 hard test cases, and none of its 29 changes against the nearest alternative was wrong when reviewed. Known gaps are listed in the notes.

**Semantic chunking signal test:** neighbouring sentences score only modestly higher than random pairs (median 0.57 against 0.47). The pre-set drop rule (more than 30% of neighbouring pairs scoring below the median random pair) was not triggered (13%), but about 40% of the lowest-scoring cuts were not real breaks, mostly speaker changes rather than topic changes. It is ranked last of the candidate strategies.

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| 0-1 | Setup, ingestion and cleaning, naive baseline RAG | done |
| 2 | Evaluation harness, calibrated LLM judge | done |
| 3 | Stage-by-stage experiments: chunking (splitter chosen; strategy comparisons next), embeddings, indexing, retrieval, query transformation, re-ranking, generation | in progress |
| 4 | Rebuild with a framework (LlamaIndex or LangChain) and compare | planned |
| 5 | Advanced RAG: corrective, self-reflective, agentic, and GraphRAG with an LLM-extracted knowledge graph | planned |
| 6 | Production concerns: latency, cost, caching, incremental indexing, tracing | planned |
| 7 | The lineage and story explorer | planned |

## Reusable components

Intended to be separable from this corpus, developed only as far as the experiments justify:

| Component | What it would do | Status |
|---|---|---|
| **Literary sentence segmentation + benchmark** | Sentence splitting tuned for historical and translated prose, with an error taxonomy (abbreviations, quotation, historical punctuation) | comparison done and splitter selected; benchmark scripts and a cleaned test set to be packaged |
| **Entity and alias registry** | Canonical entity IDs with verified aliases (Arjuna = Partha = Dhananjaya), keeping ambiguous references ("son of Pandu") unresolved without evidence | planned |
| **Lineage and narrative context** | Chunk-boundary signals beyond similarity: entity continuity, speaker turns, reference continuity, paragraph and section structure | planned |
| **RAG evaluation harness** | Retrieval and generation metrics with a frozen, calibrated judge, a locked held-out set and unanswerable questions | working, in this repo |

## Repository layout

```
config.py              all tunables (chunk size, models, k)
src/rag/               pipeline and evaluation code
scripts/               download, ingest, chunk, embed, search, evaluation runners
eval/                  question sets, labels, calibration records, results
tests/                 unit tests (retrieval, generation evaluation, metrics, chunking)
data_seed/             cleaned corpus text (committed, so a fresh checkout does not depend on the source site)
docs/                  project proposal for the reusable components
EXPERIMENTS.md         experiment log: what changed, why, before and after, conclusion
private/LEARNING.md    detailed lab notes: concepts, alternatives, results, gotchas per stage
QUESTION_LOG.md        every question asked of the system, with retrieved chunks and verdicts
```

## Run it

```bash
pip install -r requirements.txt
bash scripts/rebuild_all.sh          # download (or use data_seed/), ingest, chunk, embed
export GEMINI_API_KEY=...            # needed for answers and for the judge
python scripts/search.py "Who was Shakuntala's mother?"
python scripts/ask.py "Who was Shakuntala's mother?"
python scripts/run_retrieval_eval.py # retrieval metrics on the working set
python tests/test_metrics.py         # each test file runs on its own
```

The held-out set is locked: `run_retrieval_eval.py` and `run_generation_eval.py` refuse to run it without `--confirm-milestone`, and every held-out run is appended to `eval/heldout_runs.log` (created at run time, not committed).

## Data and licence

The source is the public-domain English translation by Kisari Mohan Ganguli, obtained from sacred-texts.com. `data_seed/` holds the cleaned paragraph text derived from it (see `data_seed/README.md`); raw pages and generated data are not committed. The Vishnu Purana (H.H. Wilson) and Harivamsha (M.N. Dutt) translations are planned additions; their licensing will be checked before any corpus text is distributed.

## Built with

Python, NumPy, sentence-transformers, BeautifulSoup, the Gemini API (`gemini-3.1-flash-lite` for answers, `gemini-3.5-flash` as the judge), spaCy, pySBD and NLTK for the segmentation experiments. Developed with Claude Code as an AI pair-programmer; the experimental design, evaluation criteria and conclusions are directed and reviewed by the project owner.
