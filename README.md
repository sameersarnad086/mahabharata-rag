# Mahabharata RAG

**Can an AI answer "How are Krishna and Arjuna related?" when no single passage says so, and when each of them goes by four different names?**

This project explores what it takes to make retrieval-augmented generation (RAG) work on one of the hardest public-domain texts there is, the *Mahabharata* (Kisari Mohan Ganguli's English translation, starting with the Adi Parva), and builds towards a **lineage and story explorer** for the Solar (Suryavamsha) and Lunar (Chandravamsha) dynasties.

## The problem

Most RAG demos run on clean modern prose. This text breaks the usual assumptions:

- **One person, many names.** Arjuna is also Partha, Dhananjaya and Phalguna; Krishna is Vasudeva, Keshava and Madhava. The effect is measurable: in our baseline, "How did Arjuna win Subhadra?" finds the right passage in first place, while "How did Partha win Subhadra?" (the same person, the same fact) finds it only in fourth.
- **One name, many people.** Several Parikshits and Janamejayas across generations.
- **A fact spread across chapters.** Krishna belongs to the Yadu line and Arjuna to the Puru line; the link runs back through Yayati, and no single paragraph says so. Multi-hop questions like this are where plain similarity search stalls.
- **Nineteenth-century translated prose.** Long compound sentences, semicolon-joined lists, and speeches wrapped in quotation marks that run across paragraphs. General-purpose text tools are not built for this: a standard sentence splitter left 21% of our long paragraphs as a single "sentence".
- **Sources disagree.** Different texts give different lineage lists. A trustworthy system should report the disagreement with citations, not silently pick one.

## The goal

1. **A lineage and story explorer.** A knowledge graph of people and relationships (father, mother, son, spouse, descendant-of), every edge carrying its source citation, combined with RAG over the texts for the story around each person and event. Graph questions (ancestors, descendants, the path between two people, common ancestors), an interactive family tree with citations on every link, and explicit handling of name ambiguity and conflicting sources.
2. **Reusable building blocks for literary and narrative text,** separable from the Mahabharata so other projects with epics, translated novels, religious and historical texts can use them.

## Ideas being explored

These are hypotheses under test, not finished components:

- **Sentence segmentation for literary text.** Do general-purpose splitters (rule-based, statistical, parser-based) hold up on translated epic prose, and does a domain-adapted one do better? Built around an error taxonomy: abbreviations, quotation handling, historical punctuation, compound sentences. Segmentation is only a means: the real test is whether retrieval improves.
- **Entity and alias resolution.** A canonical entity registry (Arjuna = Partha = Dhananjaya = Phalguna) that keeps the original mention but links it to an entity ID, and leaves ambiguous references ("son of Pandu", where Pandu had several sons) unresolved unless context supports them. Does entity-aware retrieval fix the alias failures above?
- **Narrative continuity beyond similarity.** "These eight are known as the Vasus." and "Of these, Dhara and the truth-knowing Dhruva were born of Dhumra." belong together, yet their embedding similarity is low. Can entity continuity, speaker turns, pronoun and reference continuity, and paragraph and section structure be combined with similarity to decide where one chunk should end?
- **Lineage context for retrieval.** Using the relationship graph to bring in the ancestors or siblings that a question implies but the retrieved passage never mentions.

## Method

- **A baseline first, no frameworks.** Fixed-size chunks, `BAAI/bge-small-en-v1.5` embeddings, brute-force cosine search over NumPy, and cited answers from Gemini. No vector database or RAG framework until the comparison phase.
- **An evaluation harness before any tuning.** 36 labelled retrieval questions plus 8 unanswerable ones, with a frozen split (24 working, 12 held-out; the held-out set is locked behind an explicit flag). Retrieval metrics (hit@k, MRR, nDCG, with a strict evidence-phrase check and a looser section check) and an LLM judge for correctness, faithfulness, citation support and refusals.
- **Retrieval and generation scored separately,** end-to-end and with the correct passages supplied, so a retrieval failure cannot hide as a generation failure.
- **A calibrated, frozen judge,** checked against human grades in two rounds and then fingerprinted so later comparisons cannot silently change the ruler.
- **One change at a time, criteria written down first.** Each comparison's gates, scores and winner rule are recorded before it is run.
- **Reproducible.** Embeddings and model replies are cached; a fresh checkout rebuilds from a committed copy of the cleaned corpus if the source website blocks downloads.

## Results so far

**Baseline** (nothing tuned):

| | Working set (24 questions) | Held-out (12 questions) |
|---|---|---|
| Correct passage in the top 5 (strict check) | 0.67 | 0.75 |
| Answer correctness, end-to-end | 0.81 | 0.67 |
| Answer correctness, correct passages supplied | 0.96 | 0.92 |

With the right passages the model is right 92-96% of the time; with what the system actually retrieves, it is not. **Retrieval, not generation, is the bottleneck.** All 8 unanswerable questions were correctly refused.

**Sentence segmentation** (five candidates plus a control over all 1,306 paragraphs, with hand-checked boundaries):

- About **71% of the text sits in paragraphs over 1,000 characters**, so any chunking strategy must split most of the corpus and needs reliable sentence boundaries.
- The default rule-based splitter (pySBD) treats a quote-wrapped speech as one unbreakable unit and **left 21% of long paragraphs unsplit**.
- A spaCy-based splitter with four targeted fixes (an abbreviation merge for "viz.", "i.e.", "Mr.", a lowercase merge for stray full stops, and opening and closing quote placement) passes all 13 hard test cases; none of the 29 changes it makes over its nearest alternative was wrong on review. Known gaps are in the notes.

**Semantic chunking signal test:** neighbouring sentences score only modestly higher than random pairs (median 0.57 against 0.47). A pre-set drop rule was not triggered (13% against a 30% limit), but about 40% of the lowest-scoring cuts were not real breaks, mostly speaker changes rather than topic changes, so it is ranked last of the candidate strategies.

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| 0-1 | Setup, ingestion and cleaning, naive baseline RAG | done |
| 2 | Evaluation harness, calibrated LLM judge | done |
| 3 | Stage-by-stage experiments: chunking (seven strategies; splitter chosen, comparisons next), embeddings, indexing, retrieval, query transformation, re-ranking, generation | in progress |
| 4 | Rebuild with a framework (LlamaIndex or LangChain) and compare | planned |
| 5 | Advanced RAG: corrective, self-reflective, agentic, and GraphRAG with an LLM-extracted knowledge graph | planned |
| 6 | Production concerns: latency, cost, caching, incremental indexing, tracing | planned |
| 7 | The lineage and story explorer | planned |

## Repository layout

```
config.py              all tunables (chunk size, models, k)
src/rag/               pipeline and evaluation code
scripts/               download, ingest, chunk, embed, search, evaluation runners
eval/                  question sets, labels, calibration records, results
tests/                 unit tests (retrieval, generation evaluation, metrics, chunking)
data_seed/             cleaned corpus text (committed, so a fresh checkout does not depend on the source site)
EXPERIMENTS.md         experiment log: what changed, why, before and after, conclusion
private/LEARNING.md    detailed lab notes: concepts, alternatives, results and gotchas per stage
QUESTION_LOG.md        every question asked of the system, with retrieved chunks and verdicts
```

## Run it

```bash
pip install -r requirements.txt
bash scripts/rebuild_all.sh           # download (or use data_seed/), ingest, chunk, embed
export GEMINI_API_KEY=...             # needed for answers and for the judge
python scripts/search.py "Who was Shakuntala's mother?"
python scripts/ask.py "Who was Shakuntala's mother?"
python scripts/run_retrieval_eval.py  # retrieval metrics on the working set
python tests/test_metrics.py          # each test file runs on its own
```

The held-out set is locked: the evaluation runners refuse to run it without `--confirm-milestone`, and every held-out run is appended to `eval/heldout_runs.log` (created at run time, not committed).

## Data and licence

The source is the public-domain English translation by Kisari Mohan Ganguli, obtained from sacred-texts.com. `data_seed/` holds the cleaned paragraph text derived from it (see `data_seed/README.md`); raw pages and generated data are not committed. The Vishnu Purana (H.H. Wilson) and Harivamsha (M.N. Dutt) translations are planned additions; their licensing will be checked before any corpus text is distributed.

## Built with

Python, NumPy, sentence-transformers, BeautifulSoup, the Gemini API (`gemini-3.1-flash-lite` for answers, `gemini-3.5-flash` as the judge), spaCy, pySBD and NLTK for the segmentation experiments. Developed with Claude Code as an AI pair-programmer; the experimental design, evaluation criteria and conclusions are directed and reviewed by the project owner.
