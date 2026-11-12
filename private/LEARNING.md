# LEARNING.md — my RAG notes

My personal reference for the Mahabharata RAG project. Written so I can re-read it months later and explain every
decision to someone else without opening the code. Updated at the end of every meaningful step.

Each stage follows the same layout: **Why it exists → What I decided (and why) → How it works → Tools used →
Alternatives → Gotchas → Results.**

**Contents**
1. [Named problems (shared vocabulary)](#named-problems-shared-vocabulary)
2. [The pipeline at a glance](#the-pipeline-at-a-glance)
3. [Code map: what is done where](#code-map-what-is-done-where)
4. [Decisions log](#decisions-log)
5. [Phase 0 — Setup and download](#phase-0--setup-and-download)
6. [Phase 1 — Ingestion and cleaning](#phase-1--ingestion-and-cleaning)
7. [Phase 1 — Chunking](#phase-1--chunking)
8. [Phase 1 — Embeddings](#phase-1--embeddings)
9. [Phase 1 — Retrieval (concept)](#phase-1--retrieval-concept)
10. [Known problems: where each one gets solved](#known-problems-where-each-one-gets-solved)
11. [Phase 1 — Generation](#phase-1--generation)
    - [Question log: observed failures](#question-log-observed-failures-candidates-for-phase-2)
12. [Phase 1 retrospective (final)](#phase-1-retrospective-final)
13. [Phase 2 — Evaluation (concepts, retrieval, generation)](#phase-2--evaluation-concepts-and-metrics)
    - **Concepts and rules**
        - [Why it exists](#why-it-exists-5)
        - [Score retrieval and generation separately](#score-retrieval-and-generation-separately)
        - [Rules that keep the evaluation honest](#rules-that-keep-the-evaluation-honest)
        - [The working / held-out split](#the-working--held-out-split)
    - **Retrieval evaluation**
        - [Retrieval metrics](#retrieval-metrics)
        - [The retrieval question set (36)](#the-retrieval-question-set-36-in-evalretrieval_questionscsv)
        - [Labelling the 36 questions (done)](#labelling-the-36-questions-done)
        - [How the retrieval evaluation runs, step by step](#how-the-retrieval-evaluation-runs-step-by-step)
        - [Retrieval evaluation: what was built](#retrieval-evaluation-what-was-built)
        - [Retrieval baseline results](#retrieval-baseline-results-phase-1-pipeline-full-table-in-experimentsmd)
    - **Generation evaluation**
        - [Concept: a language model as judge](#generation-metrics-a-language-model-as-judge)
        - [Overview](#generation-evaluation-what-it-is-and-how-it-runs-lesson-written-before-the-build)
        - [1. What it is and how we do it](#1-what-generation-evaluation-is-and-how-we-do-it)
        - [2. The two modes: end-to-end and ideal context](#2-the-two-ways-to-run-it)
        - [3. The metrics and how each number is calculated](#3-the-metrics-what-they-mean-how-they-are-calculated)
        - [4. How each mode ran, and the results](#4-how-each-mode-worked-in-our-first-run-and-the-results)
        - [5. What the results showed](#5-what-the-results-showed-and-what-led-to-calibration)
        - [6. Judge calibration, round 1 (and the calibration measures)](#6-judge-calibration-round-1)
        - [6a. Calibration 1 and the judge fixes](#6a-calibration-1-what-we-saw-and-the-judge-fixes-that-followed)
        - [6b. Calibration 2](#6b-calibration-2-the-independent-test)
        - [6c. Freezing the judge](#6c-decision-freeze-the-judge)
        - [6d. Official baseline, working set](#6d-the-official-baseline-frozen-judge-working-set)
        - [6e. Held-out baseline](#6e-held-out-generation-baseline-run-once)
        - [7. How a run works (worked example R01)](#7-how-a-run-works-shown-on-one-real-question-r01-who-was-sakuntalas-mother)
14. [Phase 2 retrospective (final)](#phase-2-retrospective-final)
15. [Phase 3 — Deep dive, one stage at a time](#phase-3--deep-dive-one-stage-at-a-time)
    - [Stage: Chunking — the strategies](#stage-chunking--the-strategies-learning-first-choosing-later)
16. [Public post drafts](#public-post-drafts)

---

## Named problems (shared vocabulary)

**The lineage and one person with more than one name problem** — the project's central challenge. Questions about who is related to whom (father, son, ancestor, descendant, how two people connect) are hard for a plain search over text, and the same person appears under several names (Arjuna = Partha = Dhananjaya = Gudakesha; Krishna = Vasudeva = Keshava = Madhava), spellings vary (Yudhishthira / Yudhisthira), and one name can belong to several people (the many Parikshits and Janamejayas, or "Bharata" as a person, a dynasty and a form of address). The baseline does not solve it, by design. Where it is measured and solved: "Known problems: where each one gets solved" (Phase 2 measure, Phase 3 mitigate, Phase 5 and 7 solve structurally). Evidence so far: Q1 to Q5 in `QUESTION_LOG.md`.

---

## The pipeline at a glance

```
download → ingest/clean → chunk → embed → retrieve (numpy) → generate answer (Gemini)
 (done)       (done)       (done)  (done)      (done)              (done)
```
Phase 1 baseline is complete end to end. "Index" is just a numpy array at this size; a real index (FAISS, vector database) is a Phase 3 comparison.

Rule of thumb I keep coming back to: **each stage can only pass on what the previous stage gave it.** A mistake in
ingestion is inherited by chunking, embedding and retrieval, and nothing later can repair it.

Current data flow and files (all derived data is gitignored and can be rebuilt with the scripts):

| Step | Input | Output | Script |
|---|---|---|---|
| Download | sacred-texts.com pages | `data/raw/.../section_001..237.html` (99 MB) | `scripts/download_adi_parva.py` |
| Ingest | raw HTML | `data/processed/paragraphs.jsonl` (1,306 paragraphs) | `scripts/run_ingest.py` |
| Check | paragraphs | sanity report | `scripts/report_ingest.py` |
| Chunk | paragraphs | `data/processed/chunks.jsonl` (1,670 chunks) | `scripts/run_chunking.py` |
| Embed | chunks | `data/cache/emb_*.npy` (1,670 x 384 numbers, 2.6 MB) | `scripts/run_embedding.py` |
| Retrieve | a question | the 5 closest chunks with scores and citations | `scripts/search.py` |
| Generate | question + 5 chunks | a cited answer from Gemini | `scripts/ask.py` |
| Log | a question | an entry in `QUESTION_LOG.md` | `scripts/log_question.py` |

---

## Code map: what is done where

A mental map of the project, by stage. Code that does the work lives in `src/rag/`; commands you run live in `scripts/`; checks live in `tests/`; every setting (chunk size, model names, k...) lives in `config.py`. Nothing here describes how the code is written, only what each file is for.

| Stage | Does what (plain words) | Library file (`src/rag/`) | Command file (`scripts/`) | Produces |
|---|---|---|---|---|
| **Download** | Fetch the 237 pages from the website | | `download_adi_parva.py` | the raw web pages (`data/raw/`) |
| **Ingest** | Read each page, keep only the story paragraphs, tag each with section and sub-parva, glue back paragraphs split by page breaks | `ingest.py` | `run_ingest.py` (runs it on all pages), `report_ingest.py` (sanity report), `inspect_ingest.py` (peek at a few pages) | the clean paragraphs file |
| **Chunk** | Cut the text into overlapping 1,000-character pieces, each labelled with its sections | `chunking.py` | `run_chunking.py` | the chunks file |
| **Embed** | Turn every chunk into 384 numbers; save them so they are not recomputed | `embedding.py` | `run_embedding.py` | the vectors file (`data/cache/`) |
| **Retrieve** | Turn a question into numbers, find the 5 closest chunks | `retrieval.py` | `search.py` (show the top chunks for a question) | ranked chunks with scores and citations |
| **Generate** | Build the prompt, ask Gemini, check the citations in its answer | `generation.py` | `ask.py` (question to cited answer), `list_models.py` (which Gemini models your key can use) | an answer |
| **Explore** | Ask any question and write the full result into the question log | | `log_question.py` | entries in `QUESTION_LOG.md` |
| **Evaluate retrieval** | Score how often the right passage is among the retrieved chunks | `eval_retrieval.py` (the marker), `metrics.py` (the formulas), `textnorm.py` (text matching helper) | `run_retrieval_eval.py` (the button; guards the held-out set), `make_split.py` (the practice / sealed split), `verify_labels.py` (checks every quote really is in the book) | scores in `eval/results/`, log of held-out runs |
| **Rebuild** | Recreate every generated file from scratch in a fresh session | | `rebuild_all.sh` | everything above |
| **Tests** | Automatic checks that each part behaves | | `tests/test_chunking.py`, `test_retrieval.py`, `test_generation.py`, `test_metrics.py` | pass or fail |

**Data and notes files:**
| File | What it is |
|---|---|
| `eval/retrieval_questions.csv` | the question paper with its answer key (36 questions: sections, quotes, expected answers, split) |
| `eval/README.md`, `eval/split_info.json` | the rules for the evaluation set and the recorded split |
| `eval/results/*.json`, `eval/heldout_runs.log` | saved scores, and the audit log of every sealed-set run |
| `QUESTION_LOG.md` | every informal question, with the chunks returned and a verdict |
| `LEARNING.md`, `EXPERIMENTS.md`, `HANDOFF.md`, `CLAUDE.md` | these notes; the experiment log; the status file for a new chat; the working rules |

---

## Decisions log

A quick list of what I chose, so I never have to hunt for it. Details are in the sections below.

| Decision | Choice | Why (short) | Status |
|---|---|---|---|
| HTML parser | BeautifulSoup with Python's built-in `html.parser` | Simple, common, one small dependency | Final for now |
| Cleaning happens | During ingestion, before chunking | Chunking and embedding only see strings | Final |
| Page-break fragments | Glue back (Option A: `[paragraph continues]` tag, or lowercase start after a page marker) | A third of "paragraphs" were fragments | Final |
| Closing lines ("Thus endeth the section…") | Keep as text | Real content, names the sub-parva | Final |
| `printed_page` | Store, but treat as approximate and do not cite | Marker meaning unclear | Revisit |
| Chunking strategy | Pure fixed-size, characters, may cross paragraph and section boundaries | Simplest baseline that smarter methods must beat | Baseline |
| Chunk size / overlap | 1000 / 200 characters (20%) | Inside the range the paragraph stats support; conventional | **Hypothesis, to be tested** |
| Embedding model | `BAAI/bge-small-en-v1.5` (384 dims, 512-token limit), run locally | Small, free, no truncation of our chunks; chosen from a list of options | Baseline |
| Query prefix for bge | Off | Keep one variable at a time; test on/off later | Experiment pending |
| Search method | Brute force: cosine similarity against all 1,670 vectors with numpy, top-5 | About 1.5 ms at this size; no index needed | Baseline |
| Generator | `gemini-3.1-flash-lite` via `google-genai`, temperature 0 | Cheap, current, I hold the key | Baseline; compare newer models in Phase 3 |
| Prompt | Answer only from numbered passages, cite `[n]`, fixed refusal wording, report disagreements, merge names only if a passage says so | Grounding for a lineage project | Baseline |
| Passage order | Best match first | Simplest | Experiment pending |
| Failure handling | Retry temporary Gemini errors (429, 5xx) 4 times with waits | A "high demand" 503 crashed a run | Final |

---

## Phase 0 — Setup and download

**Why it exists.** A reproducible start: one config file for every tunable, raw data cached on disk so I hit the
website once, and metadata-first thinking so citations are possible later.

**What I decided.**
- All tunables live in `config.py` (chunk size, overlap, paths, source URL). Experiments change values there, never inline.
- Source: Kisari Mohan Ganguli's translation on sacred-texts.com. The site is already split into one page per section, so section metadata comes almost free.
- The downloader saves one HTML file per page and skips files it already has, so re-running is safe. It waits one second between requests to be polite to a volunteer-run site.

**Alternatives.** Project Gutenberg plain text: no HTML to clean, but it is one big file I would have to split by parva myself.

**Gotchas.**
- **Page numbers are offset by one.** `m01001` is the Translator's Preface and `m01002` is Section I, so page = section + 1. Files are named `section_NNN.html` by *page*, so file 237 is Section CCXXXVI. Metadata must use the Roman-numeral section from the page itself, not the file number, or every citation is off by one.
- The site redirects `www.` to the bare domain; both hosts had to be allowed in the sandbox network policy.
- Each page is about 420 KB because it is full of site scripts; the real text is a tiny part of that (see Ingestion).

**Result.** 237 pages: the Preface plus Sections I to CCXXXVI.

---

## Phase 1 — Ingestion and cleaning

### Why it exists
Chunking and embedding only ever see a string of characters. They cannot tell story from website furniture. So anything I
leave in gets cut up, embedded and searched. Ingestion turns raw HTML into **clean paragraphs, each tagged with where it
came from.** Retrieval quality is capped here: no reranker or better embedding model can rescue text that should never
have been embedded.

The size of the problem, measured on all 237 files:

| | Characters | Chunks it would produce (1000/800 step) |
|---|---|---|
| Raw HTML | 99.2 million | about 124,000 |
| Actual story text | 1.34 million (**1.4%**) | about 1,700 |

Embedding the raw HTML would mean about 70 times more cost and time, and the top results could be JavaScript.

### What I decided (and why)
- **Clean first, during ingestion, before chunking.** If chunking ran first, window boundaries would be computed from text full of noise, and page markers could split sentences.
- **Never touch the raw files.** Cleaning writes to `data/processed/`. If a rule turns out wrong I re-run with a new one.
- **Keep provenance on every paragraph:** file, section heading, sub-parva, paragraph index, approximate printed page. Citations depend on it.
- **Be conservative:** drop only what I can justify (page markers, empty tags, site furniture). Do not "improve" the content, and do not normalise name spellings here; aliases are a retrieval-stage decision that I want to be able to measure.

### How it works (in plain words)
Each downloaded page is a web page. A library reads its structure and finds the one container that holds the story
(`<article data-slot="reader-content">`). Inside it, plain paragraphs are story; special paragraphs are page markers
(`p. 33`) or the sub-parva label (`(Paushya Parva)`). The code walks the paragraphs in order, remembers the latest
sub-parva and page marker, records the story paragraphs, and glues back any paragraph that a page break split in two.
The result is **1,306 clean, labelled paragraphs.**

### Tools used
- **BeautifulSoup (`beautifulsoup4`)** with Python's built-in `html.parser` backend: reads and searches the page structure. The only third-party package so far.
- Python standard library: `re` (pattern matching), `dataclasses`, `pathlib`, `json`, `urllib`.

Code: [`src/rag/ingest.py`](src/rag/ingest.py). Helpers: [`scripts/run_ingest.py`](scripts/run_ingest.py) (writes the output),
[`scripts/inspect_ingest.py`](scripts/inspect_ingest.py) (print a few files), [`scripts/report_ingest.py`](scripts/report_ingest.py)
(whole-corpus checks). A 3-file sample for reading is committed in [`samples/`](samples/ingest_sample.txt).

### Alternatives
| Option | Trade-off |
|---|---|
| Python's built-in `html.parser` alone | No dependency, but I would hand-write the "am I inside the article / a paragraph / a link" tracking. More code, more bugs. |
| `lxml` | Faster, but a compiled extra; speed is irrelevant for 237 small files. |
| Project Gutenberg plain text | No HTML, but no per-section structure. |

### Gotchas (each one is a real thing that bit me)
- **The meta description lies.** The page head contains a convenient text excerpt, but it is a truncated search-engine summary that stops mid-sentence. It looks like text and is not. Never use it.
- **"Grab every paragraph" grabs site furniture** ("No bookmarks yet", the copyright footer). Scope extraction to the article container.
- **Encoding.** The files are UTF-8. Reading them as latin-1 turns every apostrophe and dash into garbage (`â\x80\x99`), which would quietly corrupt name matching.
- **The section heading is not always in the `<h1>`.** On file 002 the `<h1>` is the book title and `SECTION I` sits in a `<div>`.
- **Page breaks split paragraphs mid-sentence.** Markers like `p. 16` (and Roman ones like `p. xii` in the preface) fall inside paragraphs. Rule I chose: glue a fragment back to the previous paragraph if it carries the site's `[paragraph continues]` tag, or if it follows a page marker and starts with a lowercase letter. Before this, about a third of the "paragraphs" on one page were fragments. 385 fragments were merged across the corpus.
- **Test on everything, not three files.** My rules worked on the first three pages. The full run found a heading written `Section CLXXVI` (mixed case) that broke the section sequence, and sub-parva labels spelled several ways for the same name (`Sambhava Parva`, `… continued`, `…, continued `). Normalised from 35 raw variants to 18 values. Without that, a filter on "Sambhava Parva" would have missed most of its text. This is the same class of problem as Yudhishthira / Yudhisthira.
- **The source's Roman numerals are non-standard for Sections 190 to 199** (`SECTION CLXL`, `CLXLI`... where standard Roman is `CXC`, `CXCI`...). A citation reading "Section CLXLI" looks like a bug. I now store a plain `section_number` (191) next to the raw heading, and the report checks that it equals the file number minus one for every file. My earlier "no gaps" check had passed only because my simple converter happens to read those forms correctly, which is luck, not a test.
- **`printed_page` is approximate.** In the preface it goes `xii` then `ix`, and it is unclear whether a marker means "page starts here" or "page ends here". Do not use it in citations yet.
- **Source typos exist** (e.g. "sixty-tour"), so exact-match search cannot assume clean spelling.

### Results
- 237 of 237 files parsed. Sections I to CCXXXVI in order, no gaps.
- 1,306 paragraphs, 1.33 million characters.
- No garbled characters, no site junk, no lowercase-start fragments left.
- Files 001 to 003 (preface, Sections I and II) have no sub-parva label, which is expected.
- Open question: `Haranaharana Parva` looks odd; probably a genuine sub-parva name, not yet checked against the Parva-sangraha list.

---

## Phase 1 — Chunking

### Why it exists
An embedding model turns a piece of text into **one** list of numbers (a vector). A whole section is thousands of words
on many topics, so one vector for it is a blurry average. The language model also has a limited reading window. So I cut
the text into **chunks**, embed each one, and later retrieve the few that best match a question.

The core trade-off, which every chunking choice is about:
- **Small chunks:** precise vectors and cheap to send to the model, but they lose surroundings. "He then went to the forest" no longer says who "he" is.
- **Large chunks:** keep context, but the vector gets blurrier and each retrieved result uses more of the model's reading window.

### The baseline strategy (what I built first, and why)
A **baseline** is the simplest reasonable version. Every later, smarter method has to beat it, and I can only claim an
improvement if I have this to compare against.

| Setting | Baseline choice | Reason |
|---|---|---|
| Method | **Pure fixed-size with overlap** | Simplest possible; no judgement involved |
| Unit | **Characters** (not tokens) | Simple and matches `config.py`; tokens become a separate experiment later |
| Boundaries | **Ignored.** The whole corpus is joined into one long string and cut; chunks may cross paragraph and even section boundaries | The deliberately "dumb" case, so structure-aware chunking shows a measurable gain |
| Size | **1000 characters** | See "How I arrived at 1000 / 200" below |
| Overlap | **200 characters (20%)** | See below |

**How it works.** Join all 1,306 paragraphs into one long text (separated by a blank line). Start at position 0 and take
1000 characters. Move forward by **800** (that is size minus overlap) and take the next 1000. Repeat until the text ends.
Neighbouring chunks therefore share 200 characters. The overlap is insurance: if a fact sits on a cut, at least one
chunk contains all of it. The number of chunks is roughly total characters ÷ 800, and 1.33 M ÷ 800 ≈ 1,670, which is
exactly what I got.

**Its known weakness.** It counts characters and ignores meaning, so it cuts mid-word and mid-sentence. For example,
"Santanu begat Bhishma on Ganga, and Vichi | travirya on Satyavati" could leave neither chunk with the whole
relationship. That is the lineage / multi-hop problem in miniature, and it is why this is a baseline and not the answer.

### How I arrived at 1000 / 200
This is the part worth being able to explain, because "1000 / 200" is a popular default and I wanted a reason beyond that.

**Step 1 — measure the paragraphs.** Before choosing a size I measured the cleaned corpus (1,306 paragraphs):

| | Characters |
|---|---|
| Median | 653 |
| Mean | 1,021 |
| 90th percentile | 2,334 |
| 99th percentile | 5,618 |
| Longest | 10,838 |

The mean is well above the median: a long tail of very long paragraphs. 35% of paragraphs are over 1,000 characters and
31% are under 400.

**Step 2 — see what each size does to those paragraphs** (with 20% overlap):

| Chunk size | Overlap | Approx. chunks | Paragraphs that fit whole | Paragraphs needing 3+ chunks |
|---|---|---|---|---|
| 400 | 80 | 4,166 | 31% | 33% |
| 600 | 120 | 2,777 | 47% | 20% |
| 800 | 160 | 2,083 | 57% | 12% |
| **1000** | **200** | **1,666** | **65%** | **8%** |
| 1500 | 300 | 1,111 | 79% | 2% |
| 2000 | 400 | 833 | 87% | 1% |

(The "fit whole" columns describe paragraph-sized pieces; the pure fixed-size baseline ignores paragraph boundaries, so
treat them as a guide to how much cutting a size causes, not an exact prediction.)

**Step 3 — bracket a sensible range.**
- Below about **600**, most paragraphs get cut apart, a third of them into three or more pieces. Too fragmented for text where the speaker tag ("Sauti said…") sits at the start.
- Above about **1,500**, chunks mostly keep whole paragraphs, but they start mixing unrelated neighbours, and the many short paragraphs get swallowed into bigger ones.
- So the sensible range is **roughly 600 to 1,500.**

**Step 4 — pick a starting point inside the range.** I chose **1000** because it is inside that range, so the stats do not
argue against it; it is a round, widely used value, which makes my results easy to compare with other people's; and it is
typically within the input limit of common embedding models (limits vary by model, so I must re-check this once I choose
one). I chose **20% overlap (200)** because that is a conventional safety margin for facts that straddle a cut, and it
keeps the extra storage modest.

**Step 5 — be honest about what the stats cannot say.** They narrow the range; they cannot pick a winner. Whether 800
beats 1000 depends on how well each retrieves the right passages for real questions. So **1000 / 200 is a hypothesis
and a baseline to beat, not a finding.** After the Phase 2 test set exists I will sweep the size one value at a time
(600, 800, 1000, 1500), log each result in `EXPERIMENTS.md`, and let the numbers decide.

### Tools used
Standard library only: `json` (read/write data), `bisect` (quickly find which paragraph a character position falls in),
`dataclasses` (the `Chunk` structure), `pathlib` (paths), `statistics` (median in the report). No new packages.

Code: [`src/rag/chunking.py`](src/rag/chunking.py) (`fixed_size_spans` = the sliding window; `build_chunks` = join, cut,
attach metadata). Checks: [`tests/test_chunking.py`](tests/test_chunking.py), 9 edge cases (empty text, shorter than one
chunk, exact fit, no overlap, last chunk shorter, bad settings, full coverage). Runner:
[`scripts/run_chunking.py`](scripts/run_chunking.py).

### Metadata on every chunk
Source, parva, **a list of sections** it touches, a list of sub-parvas, the first file and paragraph it starts in, and
character offsets. The sections are a list, not a single value, because 297 of the 1,670 chunks (18%) span more than one
section. A single value would produce wrong citations.

### Alternatives (each becomes its own one-variable experiment in Phase 3)
| Method | Idea | Best when |
|---|---|---|
| Fixed-size | Cut every N characters, with overlap | Baseline, uniform text |
| Recursive | Split on paragraph, then sentence, then word, until under N | General-purpose default |
| Sentence-based | Group whole sentences up to N | Facts live inside single sentences |
| Semantic | Cut where adjacent-sentence similarity drops | Topics shift unpredictably; costs embedding calls |
| Structure-aware | Cut on the source's own boundaries (paragraphs, speaker turns like "Sauti said…") | The text has real structure, as ours does |
| Parent-child | Embed small chunks, return the larger parent | Want precise matching and rich context |

### Gotchas
- The window must stop as soon as a chunk reaches the end of the text; otherwise the loop emits extra tail windows that add no new text.
- Overlap equal to or larger than size makes the step zero or negative and the loop never ends, so that must be rejected with an error.
- Pure fixed-size cuts mid-word (chunk 500 starts `'e numerous. And…'`).
- The chunker cannot fix aliases (Partha = Arjuna) or spelling variants. Chunk size only decides how much surrounding text carries identifying context.

### Results (baseline, not yet scored)
- 1,670 chunks. Length minimum / median / maximum = 661 / 1000 / 1000 (the 661 is just the final tail).
- 297 chunks (18%) span more than one section.
- No retrieval metrics yet; they need the Phase 2 test questions. See `EXPERIMENTS.md`.

---

## Phase 1 — Embeddings

### Why it exists
A computer cannot compare chunks by meaning if they are just text. A question like "Who was Shantanu's wife?" has to find
the chunk about Ganga and Satyavati even when they share few words. Embeddings turn text into numbers so that
"similar meaning" becomes "numerically close".

### How it works (in plain words)
- An **embedding model** reads a piece of text and outputs a **vector**: one fixed-length list of numbers (for example 384 or 1,024 of them).
- **One chunk becomes one vector**, not one number per word. Inside the model each word piece (token) gets its own vector first, but they are combined into a single final vector for the whole chunk, and that is the only one we keep.
- **The length of the list is called the number of dimensions and is fixed by the model.** Every chunk, short or long, comes out the same length, which is what makes comparison possible. bge-small gives 384; OpenAI's small model gives 1,536.
- **No single number has a human meaning** (position 17 is not "mentions Bhishma"). Meaning is spread across the whole pattern, which the model learned in training.
- **Similar meaning gives similar patterns.** "Bhishma vowed celibacy so Satyavati's sons could inherit" lands close to "Bhishma gave up the throne"; "Arjuna shot the fish's eye" lands far away.
- **Our scale:** 1,670 chunks = 1,670 vectors. With a 384-dimension model that is a table of 1,670 rows by 384 columns, about 640,000 numbers and a few MB. Searching it by brute force takes milliseconds, which is why the roadmap starts with plain NumPy and not a vector database.

### How retrieval uses it
1. Embed every chunk once, ahead of time, and save the vectors to disk.
2. At question time, embed the question with **the same model** (same length, comparable).
3. Score the question vector against every chunk vector with **cosine similarity** (the angle between two vectors; similar meaning means a small angle).
4. Return the top-k chunks (`TOP_K = 5` in `config.py`).

### Things to keep in mind
- **Changing the model means re-embedding everything**, because vectors from different models cannot be compared. So cache the vectors on disk, labelled with the model name and chunk settings.
- **Input limit.** Each model reads a maximum number of tokens and silently cuts off the rest. Our 1,000-character chunks are roughly 250 to 350 tokens, but Sanskrit names split into many pieces, so that is an estimate. A 256-token model could truncate some chunks. This links back to the chunk-size decision.
- **One chunk = one vector** is why a chunk covering many topics gives a blurry vector, and why chunk size matters.
- **Aliases and spelling variants** (Partha = Arjuna, Yudhishthira / Yudhisthira): a general-purpose model may or may not connect them. To be measured with the Phase 2 test set; keyword search (BM25) may help later.

### Options checked (October 2026; third-party sources disagree, so verify on each model card)
| Option | Type | Notes |
|---|---|---|
| bge-small-en (33M parameters) | Local, tiny | Lightweight, widely used; input limit recalled as 512 tokens, not yet verified |
| all-MiniLM-L6-v2 (384 dims) | Local, tiny | Classic tutorial model; older; recalled 256-token limit may truncate our chunks |
| EmbeddingGemma-300M | Local, small | Built for on-device use; Gemma licence terms |
| Qwen3-Embedding-0.6B | Local, small | Newer, Apache 2.0, reported 32K-token input |
| OpenAI text-embedding-3-small | API | About $0.02 per million tokens (the whole corpus costs well under a cent); reported 8,191-token limit; needs an API key |

Very large models (Qwen3-Embedding-8B, Harrier-OSS 27B) need serious hardware and do not suit this project right now.

### What I decided and built
- **Model: `BAAI/bge-small-en-v1.5`**, chosen by me from the options above. Small (33M parameters), free, runs on this machine, and its 512-token limit is comfortably above our chunks. Later (Phase 3) I compare 2 to 3 other models, one change at a time.
- **Library: `sentence-transformers`** (version 6.1.0). It loads Hugging Face embedding models and runs them with PyTorch. It is a big install (it pulls in PyTorch plus many supporting packages) but only one new package for me to name. `numpy` holds the vectors.
- **Vectors are scaled to length 1** ("normalised"). Then cosine similarity is just a multiply-and-add, which is what the search step will use.
- **Disk cache.** Vectors are saved in `data/cache/`, with a file name containing a fingerprint of the model name and every chunk's text. Change the model, the chunk size or the cleaning and the fingerprint changes, so it re-embeds. A stale cache can never be reused by accident.
- **Query prefix off.** bge models are trained to see a phrase ("Represent this sentence for searching relevant passages: ") in front of *questions* (not chunks). `config.py` has a switch, currently off, so I can test it as its own experiment.

Code: [`src/rag/embedding.py`](src/rag/embedding.py), runner [`scripts/run_embedding.py`](scripts/run_embedding.py). Settings in `config.py`
(`EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE`, `USE_QUERY_PREFIX`).

### Results (first real run)
- Model reports **384 dimensions and a 512-token limit**, matching the third-party listings I had found. Now confirmed by the model itself.
- **Token lengths of our chunks: min 165, median 247, max 399. Zero of 1,670 chunks exceed the limit**, so nothing is silently cut off. (My earlier estimate of 250 to 350 tokens per 1,000 characters was close.)
- Output: **1,670 vectors x 384 numbers = 2.6 MB**, saved to the cache. Embedding took about 1.5 minutes on CPU; a second run loads the cache instantly.
- First vector has length exactly 1.000, confirming the normalisation.

**Quick sanity check** (a throwaway test, not the evaluation): for "Who was the father of Bhishma?" the top 3 chunks were all about Bhishma, Santanu and Vichitravirya (Sections CV, CI-CII, C). For "Why did Bhishma take a vow of celibacy?" the actual vow passage (Section C) came *second*, and the third result was an unrelated vow from Section LXXVI (Kacha). So the vectors capture the topic well, but "best first" is not guaranteed. That is exactly what Phase 2 measures; I should not judge quality from two questions.

### Gotchas
- **The sandbox blocked Hugging Face** (`huggingface.co`, error 403) at first. PyPI (package downloads) worked, but model files come from Hugging Face. Fix: add the host to the environment's allowed network domains. Library install and model download are separate things.
- Token limits are in **tokens, not characters**. I checked the real numbers with the model's own tokenizer instead of trusting a rule of thumb.
- The `pip` install pulled in large GPU libraries even though we run on CPU. Harmless here, but heavy.

### Alternatives to compare later (Phase 3)
Qwen3-Embedding-0.6B (local, long input), EmbeddingGemma-300M (local), OpenAI text-embedding-3-small (API, tiny cost), and keyword/sparse search (BM25) for exact names. Also the query-prefix switch for bge.

### Where the vectors are stored
Not in a vector database. In a plain NumPy file on disk: `data/cache/emb_<model>_<fingerprint>.npy` (1,670 rows x 384 columns, 2.6 MB) plus a small `.json` label. The chunk text and labels are separate, in `data/processed/chunks.jsonl`. **Row i of the vectors is line i of the chunks file**, and that position is the only link. Both are gitignored (not on GitHub) and rebuildable. A vector database stores vectors plus an index that finds neighbours without checking all of them, and earns its place at millions of vectors, many users or live updates. At 1,670 vectors, checking all of them takes about 1.5 ms. Phase 3 steps through NumPy -> FAISS -> a vector database to see where each starts to matter.

---

## Phase 1 — Retrieval (concept)

### Why it exists
The language model can only read a few pages at once, and the corpus is 1,670 chunks. Retrieval picks the few chunks most likely to contain the answer, and only those go into the prompt. Everything the model says is limited by what retrieval hands it: if the right chunk is not in the top-k, the model cannot answer correctly from it, however good the model is.

### What happens in the background, step by step
**Offline (done once):** chunk -> embed -> save vectors. **Online (every question):**
1. **Embed the question** with the same model, giving 384 numbers.
2. **Score** it against every chunk vector. With vectors of length 1, cosine similarity is just multiplying matching positions and adding them up (a "dot product"). Done for all 1,670 chunks at once as one matrix multiplication: about 1.5 ms.
3. **Rank** by score and keep the top-k (`TOP_K = 5`).
4. **Look up** each winner's text and labels by row number.
5. **Hand over** those chunks, with citations, to the language model (the generation stage).

### What cosine similarity is
Picture each vector as an arrow in 384-dimensional space. Cosine similarity measures the **angle** between two arrows: 1.0 = pointing the same way (same meaning), around 0 = unrelated. It ignores arrow length, which is why we scale vectors to length 1 first; then it equals the dot product. Alternatives (dot product on unnormalised vectors, Euclidean distance) give the same ranking for length-1 vectors but behave differently otherwise.

### What the scores look like on our data (real numbers)
For "Who was the father of Bhishma?": scores across all 1,670 chunks ranged from **0.425 to 0.751, median 0.582**. The top five were **0.751, 0.747, 0.745, 0.736, 0.735**.
- Scores are **not probabilities** and not a percentage of "correctness". Even the median chunk scores 0.58.
- The top results are **bunched together**, so the ranking inside the top five is fragile. A tiny change (a different model, a prefix) can reorder them.
- So we can't set a simple "relevant if above X" rule. Choosing top-k is a trade-off: small k misses the answer if it ranks 6th; large k adds noise and uses more of the model's reading window.

### Real problem seen on our data: aliases
I asked the same question with two names for the same person:
- "Who is the father of **Arjuna**?" and "Who is the father of **Partha**?" returned **0 chunks in common out of 5**.
- The Arjuna results began with a water-vessel scene and a battle scene; the Partha results with lists of Nakshatras and descendants of Soma. Neither obviously shows the answer (judged by eye on the first 90 characters only; Phase 2 measures this properly).
- The corpus uses "Arjuna" in about 240 chunks and "Partha" in about 64. The model does not reliably treat them as the same person.
- This is the lineage and one person with more than one name problem in action. Candidate fixes for later: query rewriting that adds known aliases, a name-alias table, keyword search (BM25) combined with vectors (hybrid), or a knowledge graph (Phase 5).

### Things retrieval cannot do
- **Multi-hop questions** ("how are Krishna and Arjuna related through Yayati?"): no single chunk holds the answer, and top-k returns chunks similar to the question, not a chain of facts. Needs query decomposition or a knowledge graph.
- **Exact names and rare words** can be diluted in vector space; keyword search is better there.
- **"I don't know":** it always returns k chunks, even when nothing relevant exists. The generation stage must judge that.

### Alternatives and extensions (all planned for Phase 3)
| Idea | What it adds |
|---|---|
| Metadata filters | Restrict to a sub-parva or section before ranking |
| MMR (maximal marginal relevance) | Avoid five near-duplicate results; diversify |
| Hybrid search (BM25 + vectors, combined with reciprocal rank fusion) | Exact names plus meaning |
| Query transformation (rewriting, multi-query, HyDE, decomposition) | Fix aliases and multi-hop questions |
| Reranking (cross-encoder or LLM) | Retrieve 20-50 loosely, then re-score the shortlist precisely |
| Approximate indexes (FAISS IVF/HNSW) | Speed at millions of vectors; unnecessary at 1,670 |

### How we will judge retrieval (Phase 2)
Not by eye. **Recall@k** (is a correct chunk in the top k?), **MRR** (how high is the first correct chunk?), **nDCG** (are better chunks ranked higher?), measured on a question set with known source sections.

### What I built (baseline retrieval)
- [`src/rag/retrieval.py`](src/rag/retrieval.py): a `Retriever` that loads the chunks, the cached vectors and the model, then `search(question, k)` embeds the question, scores it against all 1,670 vectors (one matrix multiply), picks the k best with `numpy.argpartition` (faster than sorting everything, then orders just the winners), and returns each hit with its rank, score, chunk id, citation and text. Only `numpy` is used for the search.
- [`scripts/search.py`](scripts/search.py): command-line tool, e.g. `python scripts/search.py "Who was Shakuntala's son?" -k 3`.
- [`tests/test_retrieval.py`](tests/test_retrieval.py): 7 checks of the ranking logic (best first, k larger than the data, k of zero, empty input, ties in a stable order, and that a dot product of unit vectors equals cosine similarity).
- **Citation format:** `Mahabharata (Ganguli), Adi Parva, Sections 191-192 (Swayamvara Parva) [section_192.html, para 1]`. It uses plain section numbers, lists the range when a chunk spans sections, and names the sub-parva.
- **Gotcha found while testing:** `argpartition` returns its picks in no guaranteed order, so tied scores could come out in a random order. Fixed by sorting the picked indices first, so ties are deterministic.

First real outputs (informal): "Why did Bhishma take a vow of celibacy?" returned Section 102 (the context leading to the vow), Section 100 (the vow itself, ranked second) and an unrelated vow from Section 76. "Who was Shakuntala's son?" returned Section 74 (Dushmanta cherishing his son by Sakuntala) first and two loosely related passages after, with scores bunched at 0.69. On-topic, but best-first is not reliable. Phase 2 will put numbers on that.

---

## Phase 1 — Generation

### Why it exists
Retrieval hands over 5 chunks; a language model reads them and writes the answer. The model never sees the other 1,665
chunks and does not search. Its answer can only be as good as the 5 chunks it receives, which is why retrieval quality
caps answer quality.

### How it works (in plain words)
One call to the model with two parts:
- **System prompt (the rules):** answer only from the numbered passages; cite every claim like `[2]`; if the passages do not contain the answer, say so in fixed wording; report disagreements between passages instead of picking one; treat two names as the same person only if a passage says so.
- **User message:** the 5 passages, each numbered and labelled with its citation, best match first, then the question.

After the call, a small checker finds every `[n]` in the answer and flags any number that was never provided (a made-up citation). That does not prove a cited passage supports the claim; that is the faithfulness check in Phase 2.

### Decisions
| Decision | Choice | Why |
|---|---|---|
| Generator | **Gemini 3.1 Flash-Lite**, planned comparison against Gemini 2.5 Flash | Cheapest current Gemini I would trust for "read 5 passages and write a short cited answer"; I already hold a Gemini key. Prices checked via third-party blogs: $0.25 in / $1.50 out per million tokens, about $0.001 per question. Verify against Google's own pricing page. |
| Model id | `gemini-3.1-flash-lite` in `config.py`, **verified** with `scripts/list_models.py` | The id exists exactly as written. The list also shows newer models the blogs I read did not mention (for example `gemini-3.5-flash-lite`, `gemini-3.5-flash`). Prices for those are unchecked; candidates for the Phase 3 model comparison. |
| Library | **`google-genai`** (2.30.0), Google's current official Python SDK; the older `google-generativeai` package is being phased out | Needs the `GEMINI_API_KEY` environment variable. |
| Temperature | 0 | As repeatable as possible, which matters when I compare runs. |
| Passage order | Rank order (best first) | Simplest; reordering is a Phase 3 experiment. |
| Thinking tokens | Not capped yet | Gemini's reasoning models bill hidden "thinking" as output tokens. `ask.py` prints the thinking-token count so I can see whether it matters before deciding to cap it. |
| Rejected: a Claude model | Not chosen | Would also work (no Claude key available here); Gemini key is what I have. Can be added later as a comparison. |

Code: [`src/rag/generation.py`](src/rag/generation.py) (`build_prompt`, `generate_answer`, `check_citations`),
[`scripts/ask.py`](scripts/ask.py) (retrieve + answer; `--dry-run` shows the prompt without calling the model),
[`scripts/list_models.py`](scripts/list_models.py), [`tests/test_generation.py`](tests/test_generation.py) (9 checks of prompt
building and citation checking; no model call).

### What I observed before the first live call
The dry-run prompt for "Why did Bhishma take a vow of celibacy?" put the Amba passage (Section 102) first and the passage
with the actual vow (Section 100) second. The model will see both, so it can still answer, but it shows that the
generator is limited by what retrieval supplies and in what order.

### First live results (informal, 2 questions; Phase 2 will measure properly)
Setup check: key works; model `gemini-3.1-flash-lite`; about 1,500 prompt tokens and 36 to 51 output tokens per question (no thinking tokens reported), which is roughly a tenth of a cent per question at the blog prices.

| Test | What happened | Verdict |
|---|---|---|
| "Why did Bhishma take a vow of celibacy?" | Answer: to serve his father Santanu and settle the matter of his children [2]; he pledged to renounce the three worlds rather than renounce truth [5]. | **Supported but incomplete.** Both citations are real: [2] is the vow passage and [5] contains the "renounce three worlds" pledge. But [5] is a later conversation with Satyavati, so the second sentence is true yet does not explain *why* he took the vow. The key reason (so Satyavati's sons would inherit) is only implied. |
| "Who won the 1990 cricket world cup?" (not in the book) | "The provided passages do not answer this question." plus one sentence on what the passages do cover. | **Refusal rule works.** |

What this shows: grounding and citations work mechanically, but answer *quality* depends on which 5 passages arrive and in what order (the best passage was ranked second, below the Amba passage). A citation check proves a cited passage exists, not that it answers the question; only the Phase 2 faithfulness and relevance measures can tell those apart.

### A prompt bug I caught in review
My first system prompt said "Arjuna, Partha and Dhananjaya are the same person" while also telling the model to use only
the passages. That quietly lets outside knowledge in and contradicts the grounding rule. Reworded so the model treats names
as the same person only when a passage says so. Lesson: examples inside a prompt are instructions too.

### Gotchas
- **I wrongly told the user a new session was needed for the key.** I had seen it unset right after it was saved and assumed environment variables only load at session start. A few minutes later the running session could see it. Lesson: re-check before prescribing a workaround, and don't state a guess about how the platform works as if it were fact.
- **A fresh session does start with an empty disk** (this part was right). Raw pages, processed data, vectors and installed packages are all gone; only committed files remain. `scripts/rebuild_all.sh` recreates everything (about 6 to 8 minutes), which also proves the pipeline is reproducible from the code alone.
- Google's API returned 403 "unregistered callers" when called without a key. That means the network path works; it is not a sandbox block (compare the Hugging Face block earlier, which failed at the connection).

---

## Known problems: where each one gets solved

The rule I follow: **measure a problem in Phase 2, mitigate it with a targeted technique in Phase 3, and only reach for
structural fixes (graphs, agents) in Phase 5 and 7 if the cheaper fixes are not enough.** Solving things in this order
means I can prove each fix helped, and I don't build a knowledge graph to fix something a keyword index would have fixed.

### 1. The lineage and one person with more than one name problem: many names for one person (Arjuna = Partha = Dhananjaya = Gudakesha; Krishna = Vasudeva = Keshava = Madhava)
**Evidence from Phase 1:** the questions "Who is the father of Arjuna?" and "...of Partha?" shared **0 of 5** top results.
"Arjuna" appears in about 240 chunks and "Partha" in about 64, and the model does not reliably treat them as one person.

| Phase | What I do | Why then |
|---|---|---|
| **Phase 2 (evaluation)** | Add alias questions to the test set: the same question asked with different names for the same person, plus a metric for how much the answers differ. | Can't fix what I can't measure. This gives the before-number. |
| **Phase 3: Embeddings** | Compare embedding models on the alias questions. Some may link names better than others. | Cheapest possible fix: swap the model. |
| **Phase 3: Retrieval** | Hybrid search: keywords (BM25) combined with vectors. | Exact names get matched even when the vector is vague. Does not by itself connect two different names. |
| **Phase 3: Query transformation** | Query expansion: add known aliases to the question (an alias table) or let the language model rewrite it. | Directly bridges "Partha" to "Arjuna" at search time. |
| **Phase 3: Ingestion (optional)** | Tag each chunk with the people it mentions, using the alias table. | Moves the work to index time; enables filtering by person. |
| **Phase 5: GraphRAG** | Extract people and relationships from the text into a graph, with one node per person and all names attached to it. | The structural fix: entity resolution (deciding "Partha" and "Arjuna" are one node). |
| **Phase 7: Lineage project** | Curated alias table plus graph; every alias carries its source citation. | Needed anyway for the family-tree explorer. |

Related name problems, same approach: **spelling variants** (Yudhishthira / Yudhisthira) go in the same alias table, and
**same name, different people** (several Parikshits and Janamejayas) needs the graph and generation prompts that
distinguish generations; filters on sub-parva help a little.

### 2. Multi-hop questions ("how are Krishna and Arjuna related through Yayati?")
No single chunk holds the answer; top-k returns chunks that resemble the question, not a chain of facts.
| Phase | What I do |
|---|---|
| Phase 2 | Include multi-hop questions in the test set, labelled as such, so I can see recall drop on them specifically. |
| Phase 3: Query transformation | **Decomposition** (split into sub-questions: Krishna's ancestors, Arjuna's ancestors, then find the common one) and **multi-query** (several phrasings, merge the results). |
| Phase 5: Agentic RAG | Let the model retrieve, read, then decide what to look up next, in a loop. |
| Phase 5 and 7: GraphRAG / knowledge graph | Answer lineage questions by walking the graph (paths, common ancestors), then use RAG for the story context. This is the real fix for lineage. |

### 3. Exact names and rare words get diluted in vector space
| Phase | What I do |
|---|---|
| Phase 3: Embeddings | Add a sparse / keyword index (BM25) alongside the dense one. |
| Phase 3: Retrieval | **Hybrid search** with reciprocal rank fusion (RRF) to merge both rankings. Metadata filters (sub-parva, section) narrow the pool. |
| Phase 3: Reranking | A cross-encoder re-reads the top 20 to 50 against the question and fixes the order. |

### 4. "I don't know": retrieval always returns k chunks, even when nothing relevant exists
| Phase | What I do |
|---|---|
| Phase 2 | Put **unanswerable questions** in the test set, and measure faithfulness (does the answer stick to the retrieved text?) with an LLM judge. |
| Phase 3: Generation | Prompt rules ("answer only from the passages; otherwise say you cannot find it"), citation requirements, and possibly a minimum-score threshold (needs care: scores are not probabilities). |
| Phase 5: Corrective RAG / Self-RAG | The system grades its own retrieved chunks and retries or abstains when they are weak. |

### 5. Conflicting sources (different texts give different lineage lists)
Needs more than one source, so it starts in **Phase 3 and 7** when the Vishnu Purana and Harivamsha are added. Every
chunk and graph edge already carries its source, so disagreements can be reported with citations instead of silently
picking one.

---

## Question log: observed failures (candidates for Phase 2)

Informal questions I asked the baseline, with what went wrong. **The full record of every question (the answer, the five chunks with ids, scores, sections and files, which were cited, and the verdict) is in [`QUESTION_LOG.md`](QUESTION_LOG.md); `scripts/log_question.py` adds new entries.** These are **not** the evaluation set; they are leads for
questions to write in Phase 2. The evaluation set itself is never edited to make results look better.

### Q1. "Why did Bharata grow up away from his father?" (retrieval miss, correct refusal)
- **Result:** the model answered "The provided passages do not answer this question". The book does cover it (Bharata is the son of Dushmanta and Sakuntala; the hermitage scene is Section 74). Generation behaved correctly given what it was handed; **retrieval failed**.
- **Top 5 retrieved:** Sections 128, 123, 191-192, 129, 110-111, all about Pandu's sons or the princes' upbringing.
- **Where the relevant text ranked (of 1,670 chunks):** chunk 580 (Section 74, mentions the childhood name Sarvadamana) **351st**; chunk 600 (Section 74, "this son shall be known as Bharata") **133rd**; the Section 68-69 chunks where Janamejaya asks about Bharata's birth and life 608th to 731st. Reworded to name Dushmanta and the hermitage: still 404th. Reworded to "Who was Sakuntala's son and where was he raised?": 33rd, still outside the top 5.
- **"Bharata" is a weak search term:** it appears in 255 of 1,670 chunks (15%). In Sections 68 to 77 every use except chunk 600 is a form of address ("O Bharata", "of Bharata's race"). Section 76 (Kacha and Devayani) has three such chunks; one of them ranked 29th, above the real story chunk, so a shared word gave a misleading pull.
- **Hypotheses (not yet separated by experiment):**
  1. Alias: the key passage uses the childhood name Sarvadamana.
  2. Same word, different meaning: "Bharata" as person, dynasty and form of address.
  3. The question's other words ("grow up", "away from his father") resemble generic upbringing passages.
  4. The story spans Sections 69 to 74, so no single chunk holds the answer (chunking).
  5. A small dense model scores overall topic, not exact words, so a single name barely moves the score.
- **Where each is tested later:** 1 and 2 in Phase 3 query transformation (add known names and context to the query) and hybrid search (keywords plus vectors); 4 in Phase 3 chunking (larger or structure-aware chunks, parent-child); 5 in Phase 3 embeddings (compare models, add keyword search); 3 in Phase 3 reranking. Entity resolution (one node per person with all names) is the structural fix in Phase 5 and 7.
- **Lesson:** a refusal is the right output when the passages do not contain the answer, but it hides a retrieval failure from the user. In Phase 2, score retrieval separately from generation so a miss like this is visible as a miss, not as a "correct refusal".
- **My (the learner's) observations, and what we concluded:**
  1. I pointed at the passage that mentions "Bharata" (I called it Section 76, the number I saw on the website) and wondered why it was not picked. It is Section LXXIV (74), file `section_075.html`. Its chunk 600 explains *the name* (a voice from heaven tells Dushmanta to cherish his son, "he shall be known as Bharata, the cherished"); it says nothing about where the boy grew up. The upbringing is in chunk 580, where he is called Sarvadamana.
  2. Conclusion: retrieval here is **semantic, not keyword**. A chunk is scored by overall meaning, so containing the word "Bharata" is neither necessary nor sufficient. It was reasonable for the name-giving chunk to rank low for an upbringing question.
  3. Verdict: an **explainable failure, fixable later** (not a good result): none of the correct passages is in the top 5, so recall@5 = 0 for this question. The cause (the passage uses a different name for the same person) is exactly what plain semantic retrieval cannot bridge.
- **Numbering gotcha (found in this conversation):** the same page has three numbers: the printed heading (SECTION LXXIV), the file name (`section_075.html`, always heading + 1), and the number the website shows (76; where it comes from is unverified). Citations print the heading number and the file name. Idea pending: add the page's web address to every citation so a reader can click through.

### Round 2: four more questions (Q2 to Q6)
Run through the full pipeline (retrieve 5, answer with Gemini 3.1 Flash-Lite). Each cited passage was checked by hand.

| # | Question | What the system did | Check against the text | Verdict |
|---|---|---|---|---|
| Q2 | Who was the father of Pandu? | Refused: passages discuss Pandu's children, death and race but not his father. | The answer is in Section 106 (Krishna-Dwaipayana begot Pandu on Ambalika). Those chunks ranked **46th, 68th and 176th**; none in the top 5. | **Retrieval miss**, correct refusal |
| Q3 | Who is the father of Arjuna? | "Son of Pandu [4][5]. Additionally son of Indra [3]." | [3] says "born as Indra's son and known as Arjuna, the mighty son of Pandu" (supports both). [5] has Arjuna saying "I am Dhananjaya, the son of Pandu and Kunti" (supports Pandu). **[4] supports neither** (it is about Subhadra). | **Right answer, one unsupported citation** |
| Q4 | Who is the father of Partha? | Refused: passages are about the Vasus, Tansu's descendants, Kalmashapada. | Same fact as Q3; the corpus even says "Dhananjaya, the son of Pandu". Top 5 had nothing relevant. | **Retrieval miss**, correct refusal |
| Q5 | How are Krishna and Arjuna related through Yayati? | Refused: passages cover Krishna and Arjuna's identities and exploits but not Yayati. | Expected: no single chunk holds the chain Krishna, Yadu, Yayati, Puru, Arjuna. | **Expected multi-hop failure**; refusal explanation is honest |
| Q6 | Who killed Karna in the Kurukshetra war? | "Arjuna slew Karna in single combat [3]." | [3] is the contents summary in Section II (Parva-sangraha) of the whole epic: "Then Arjuna slew the great Karna in single combat." | **Grounded**: answered from the passage, not from memory |

What this round showed:
- **Q3 vs Q4 is the cleanest alias demonstration so far:** the same question with two names for the same person gives an answer for one and a refusal for the other.
- **Refusals are mostly retrieval misses, not generator caution.** In Q2 and Q4 the book does contain the answer. Three of the five questions (Q2, Q4, Q5) ended in a refusal.
- **The citation check is too weak.** It only confirms the cited passage number exists (Q3's [4] passed it). Whether a cited passage supports the claim is the faithfulness measure in Phase 2.
- **Near-duplicate results waste top-5 slots.** In Q2 results [1] and [4] come from the same place (Section 126, `section_127.html` para 2), and in Q6 results [3] and [5] both begin at the same spot of Section II. With 200 characters of overlap, neighbouring chunks of one passage can both rank. Candidate fix in Phase 3: diversity ranking (MMR) or de-duplication.
- **The grounding rule held:** Q6 asks about the war, which Adi Parva does not narrate, yet the system answered only because Section II summarises the later parvas. It did not use outside knowledge. The earlier cricket question (not in the book at all) was refused correctly, so both directions of the rule have now been seen.
- **Tally (informal, 6 questions in all, not a metric):** 3 answered with support (Q1 partly, Q3, Q6), 3 retrieval misses (Q1, Q2, Q4), 1 expected multi-hop failure (Q5), 1 correct out-of-book refusal (cricket).

### Operational gotcha: Gemini 503 "high demand"
During this round Gemini returned a temporary 503 error and the run crashed. Added retry with waiting (2, 4, 8, 16 seconds) for temporary errors (429 and 5xx) in `generate_answer`; other errors (such as a bad request) are not retried. Four tests cover it. Lesson: any pipeline that calls an outside service needs retries, and temporary failures must not look like wrong answers.

## Phase 1 retrospective (final)

**Rule (also in `CLAUDE.md`):** at the end of every phase I write a retrospective: what worked, what did not, how it
compares with standard RAG practice, and what that means for the next phase.

### Verdict
**Phase 1 is complete as a baseline.** A question goes in and a cited answer comes out, built from my own pipeline with no
framework. It is **not scored**: everything below that sounds like quality is observation from 8 hand-checked questions,
not measurement. Measuring is Phase 2.

### The pipeline in numbers
| | |
|---|---|
| Source | 237 pages (preface + Sections I to CCXXXVI), 99 MB of HTML of which 1.4% is story text |
| Paragraphs | 1,306 (385 page-break fragments glued back) |
| Chunks | 1,670 (1000 chars, 200 overlap); 18% span more than one section; 165 to 399 tokens each, none over the 512 limit |
| Vectors | 1,670 x 384 numbers, 2.6 MB; embedding took about 1.5 minutes on CPU |
| Search | about 1.5 ms per question |
| Answer | about 1,500 tokens in and under 60 out per question, roughly a tenth of a cent at blog prices (unverified) |
| Tests | 29 checks across chunking, retrieval and generation, all passing |
| Rebuild from scratch | `bash scripts/rebuild_all.sh`, about 6 to 8 minutes |

### What worked
- **Looking at the data before building.** Measuring the HTML, the paragraph lengths and the token counts removed guesswork at three separate decisions.
- **Cleaning in ingestion, with provenance kept.** Every chunk traces back to section, sub-parva, file and paragraph, so citations are possible.
- **Small review, then whole-corpus checks.** Three files by eye found the page-break problem; running all 237 found a mixed-case heading and sub-parva spellings, and a later check found the source's odd Roman numerals.
- **Caching with a fingerprint** and a **one-command rebuild**: experiments are cheap to re-run and nothing depends on a particular session's disk.
- **A deliberately simple baseline.** Plain fixed-size chunks plus a small local model gives every later change something to be measured against.
- **Grounding held in both directions.** The model answered from passages when they held the answer (Karna, Arjuna) and declined when they did not (cricket, Yayati). It did not fall back on memory of the epic.
- **Logging every question with the retrieved chunks** (`QUESTION_LOG.md`) turned vague impressions ("it missed Bharata") into specific ranks and causes.

### What did not work, with the evidence
- **The lineage and one person with more than one name problem is not solved by the baseline, by design.** Plain semantic search retrieves passages that *resemble* a question. It does not know that Arjuna, Partha and Dhananjaya are one person, or that "the father of Pandu" has two answers in the text (the nominal father Vichitravirya and the biological father Vyasa), or that Krishna's line (Yadu) and Arjuna's line (Puru) meet at Yayati.
  - **Evidence:** Q3 vs Q4 (an answer for "Arjuna", a refusal for "Partha"); Q1 (the boy is "Bharata" in one passage and "Sarvadamana" in another); Q2 (the answer ranked 46th at best); Q5 (the Yayati chain exists in no single chunk).
  - **Why I am not fixing it in Phase 1:** I cannot prove a fix helps without the Phase 2 numbers, and the cheap fixes may not be enough.
  - **Where it is solved:** measured in Phase 2 (alias and lineage questions in the test set); mitigated in Phase 3 (alias expansion, keyword plus meaning search, query decomposition); solved structurally in Phase 5 (GraphRAG, one node per person with all their names) and Phase 7 (the lineage project, with a citation on every family link). The full plan is in "Known problems: where each one gets solved".
- **Retrieval is the weak link, not generation.** Of the 4 refusals on questions the book can answer or that need the book, 3 were retrieval misses (Q1 Bharata, Q2 Pandu's father, Q4 Partha's father): the answer exists but ranked 46th to 351st out of 1,670. When the right passages did arrive, the generator was accurate.
- **Aliases.** The same question gave an answer for "Arjuna" and a refusal for "Partha".
- **Names that mean several things.** "Bharata" is in 255 of 1,670 chunks, mostly as "O Bharata", so it carries almost no signal.
- **Multi-hop questions** (Krishna and Arjuna through Yayati) cannot be answered from any single chunk.
- **Near-duplicate results.** Overlapping neighbouring chunks of one passage can take two of the five slots.
- **Weak citation check.** It verifies that a cited number exists, not that the passage supports the claim (Q3 cited a Subhadra passage for "son of Pandu").
- **Fixed-size cuts** fall mid-word and split stories (the Bharata story spans Sections 69 to 74).
- **`printed_page` is unreliable**, so it is not used in citations.

### Informal scorecard (8 questions; not a metric)
| Outcome | Questions |
|---|---|
| Answered, supported | Q3 (one bad citation), Q6 |
| Answered, supported but incomplete | Q7 |
| Retrieval miss, refused | Q1, Q2, Q4 |
| Expected multi-hop failure, refused | Q5 |
| Correct refusal, not in the book | Q8 |

### Mistakes made along the way (and the lesson from each)
- I told you a new session was needed for the API key; it was not. **Lesson:** re-check before prescribing a workaround, and do not state a guess about how a platform works as fact.
- I kept saying PR #1 was open after it had been merged, and pushed later work to an already-merged branch. **Lesson:** verify the state of a pull request before talking about it. Fixed by tidying the branch and opening PR #2.
- My first system prompt said "Arjuna and Partha are the same person" while also forbidding outside knowledge. **Lesson:** examples inside a prompt are instructions too.
- The "no gaps in section numbers" check had passed only because a simple converter happened to read the source's non-standard numerals. **Lesson:** a check that passes by luck is not a check.
- A Gemini "high demand" error crashed a run. **Lesson:** anything that calls an outside service needs retries.
- The word "section" meant three different numbers (heading, file name, website). **Lesson:** make citations unambiguous; adding the page's web address is still pending.

### How this compares with standard RAG practice
| Standard practice | Where I am |
|---|---|
| Clean and parse the source properly before indexing | Done |
| Keep metadata on every chunk for filtering and citations | Done |
| Chunk by structure, not just by character count | Not yet; baseline is deliberately naive |
| Hybrid search (keywords plus vectors) | Not yet |
| Query rewriting, expansion, decomposition | Not yet |
| Rerank the shortlist | Not yet |
| Diversity ranking (avoid near-duplicates) | Not yet |
| Grounded answers, citations, "I don't know" | **Done**, with a weak citation check |
| An evaluation set and metrics before tuning | **Not yet; this is the gap that matters most** |
| Retrieval and generation scored separately | Not yet; Phase 2 |

### What Phase 2 should do (measurement, not new techniques)
1. **Write the question set** (you write it; I help structure it). Mix: plain facts; alias pairs asking the same thing under different names; multi-hop; unanswerable; ambiguous names. For each, record the expected answer and the **source section(s)** (heading number and file name, so retrieval can be scored).
2. **Score retrieval separately from generation:** recall@k, MRR, nDCG, so a miss shows up as a miss and not as a "correct refusal".
3. **Score generation:** faithfulness (does each cited passage actually support the claim?) and answer relevance, using a language model as judge. Use a different model from the generator where possible.
4. **Never edit the set to flatter results.** Questions added later go in a clearly marked separate section. Q1 to Q8 in `QUESTION_LOG.md` are seeds, not the set.
5. **Record the baseline numbers** in `EXPERIMENTS.md` as the reference for every Phase 3 comparison.

### What Phase 3 will likely test first (hypotheses, to be ordered by the Phase 2 numbers)
1. Query expansion with known aliases (Arjuna, Partha, Dhananjaya...) and query rewriting.
2. Hybrid search: keywords plus vectors, merged with reciprocal rank fusion.
3. Chunking: structure-aware and parent-child (return the surrounding passage); diversity ranking against near-duplicates.
4. Reranking the top 20 to 50 with a cross-encoder or language model.
5. Other embedding models, and the bge query prefix on/off.
6. Generation: citation verification, passage order, newer Gemini models.
Each is one change at a time, logged in `EXPERIMENTS.md`. Entity resolution (one graph node per person with all names) and multi-hop answering stay in Phases 5 and 7 unless the cheaper fixes close the gap.

### Carried over
PR #2 awaits merge; page web address in citations; the website's section numbering (unverified); `Haranaharana Parva` spelling unchecked; prices from third-party blogs unverified.

---

## Phase 2 — Evaluation: concepts and metrics

*Status: concepts learned; retrieval question set (36) labelled and split; retrieval metrics built and tested; retrieval baseline scored (working set and, once, held-out); generation evaluation not started.*

### Why it exists
Until now quality was judged by reading 8 answers and forming impressions. That cannot tell me whether a change helped:
if I change the chunk size, I cannot separate "better" from "I asked different questions". An **evaluation set** is a fixed
list of questions with known right answers and known source sections. After every change I re-run the same list and
compare numbers. It is what makes Phase 3 honest: each experiment either moves a number or it does not.

### Score retrieval and generation separately
| Stage | Question it answers | Example failure from Phase 1 |
|---|---|---|
| Retrieval | Did the right passages reach the model? | Pandu's father: the answer ranked 46th, so the model had nothing to use |
| Generation | Given the passages, was the answer correct and honest? | Arjuna: right answer, one citation that supported nothing |

If only the final answer is scored, a retrieval miss looks like a "correct refusal" (Q1, Q2, Q4). Splitting the two tells
me which stage to fix.

### Retrieval metrics

Four words used below:
- **k:** how many top results we look at. We use k = 5, written "@5".
- **rank:** a result's position in the returned list; rank 1 is the best match.
- **gold:** the sections (or evidence phrases) a person labelled as containing the answer to a question.
- **hit:** a returned chunk that matches the gold label. Anything else is a miss.

Every metric is worked out per question and then averaged over all questions in the set.

| Metric | Meaning (plain words) | How it is calculated | Example | Notes |
|---|---|---|---|---|
| **Hit rate@k** | Out of all questions, how often did retrieval put at least one right passage in the top k? "Did we find anything useful at all?" | For each question: 1 if any of the top k chunks is a hit, otherwise 0. Average over all questions. | 10 questions. For 6 of them at least one of the top 5 chunks came from a gold section. Hit rate@5 = 6 / 10 = 0.6 (60%). | The easiest to read and the most robust, because it does not need the full list of relevant passages. Our headline number. It ignores how many right passages were found and how high they sit. |
| **Precision@k** | Of the k chunks handed to the model, how many were useful? "How much noise did we send?" | (number of hits in the top k) divided by k. Average over questions. | The top 5 contains 2 hits. Precision@5 = 2 / 5 = 0.4. | Penalises noise, which matters because irrelevant passages can distract the language model. If only one passage can be right, the best possible score at k = 5 is 0.2, so a low value is not automatically a failure. |
| **Recall@k** | Of all the relevant passages that exist, how many did we bring back? "Did we find everything we needed?" | (number of gold sections found in the top k) divided by (number of gold sections labelled for that question). Average over questions. | A question has 3 gold sections and the top 5 covers 2 of them. Recall@5 = 2 / 3 = 0.67. | Only as complete as our labels: a correct passage we did not label counts as a miss. Matters most for multi-hop questions, which need several passages together. For open facts we label a "gold minimum", so treat it as secondary to hit rate. |
| **MRR** (mean reciprocal rank) | How near the top does the first right passage sit? "How quickly would a reader find a good one?" | Per question: 1 divided by the rank of the first hit (0 if there is no hit in the list). MRR is the average of that over all questions. | First hit at rank 1 scores 1.0, rank 2 scores 0.5, rank 4 scores 0.25, no hit scores 0. Three questions scoring 1.0, 0.5 and 0 give MRR = 0.5. | Looks only at the first hit, and the score falls steeply. Two systems with the same hit rate can differ in MRR, because one puts the answer first. Good when one passage is enough. |
| **nDCG** (normalised discounted cumulative gain) | How good is the whole ordering? Are the relevant passages near the top, with the best ones first? | (1) Give each returned chunk a gain: 1 if relevant, 0 if not (or a grade such as 2 = perfect, 1 = partial). (2) Divide each gain by log2(rank + 1), so lower positions count less. (3) Add them up: this is DCG. (4) Divide by the DCG of the best possible ordering for that question. The result runs from 0 to 1. | Two relevant chunks. At ranks 1 and 2 the order is ideal: nDCG = 1.0. At ranks 3 and 5: DCG = 0.50 + 0.39 = 0.89, ideal DCG = 1.00 + 0.63 = 1.63, nDCG = 0.89 / 1.63 = 0.54. | The most complete score: it handles several relevant passages and partly relevant ones. Also the hardest to explain. Depends heavily on labelling quality. The position discounts are: rank 1 = 1.00, rank 2 = 0.63, rank 3 = 0.50, rank 4 = 0.43, rank 5 = 0.39. |

### Where "relevant" comes from: the metrics do not know, we tell them
The metrics derive nothing about relevance. They compare what retrieval returned against labels a person wrote. After that
it is pure arithmetic.
| Needs a person | Computed automatically |
|---|---|
| The questions | What retrieval returned, with ranks and scores |
| The gold sections (and evidence phrases) for each question | Hit rate, precision, recall, MRR, nDCG, and their averages |
| The short expected answer (for generation scoring) | Refusal detection |
| Which questions are unanswerable | Faithfulness: a language model reads the answer plus the passages it was given (no labels needed) |
| | Answer correctness: a language model compares the answer with the expected answer |

This works because every chunk carries `section_numbers` (metadata from day one). The check "is any returned section in the gold set?" is a simple overlap test.

### Traps
- **Unlabelled correct passages count as misses.** If retrieval returns a Section 134 chunk that truly says "Arjuna, son of Pandu" but I only labelled {67, 217}, the metric blames retrieval for something it did right. Defences: label generously; read the misses of the baseline by hand once; **if labels are ever added, re-score every earlier run with the new labels** so comparisons stay fair.
- **"All relevant passages" is unknowable for open facts.** "Arjuna is Pandu's son" is stated all over the epic. So I label a **gold minimum** (sections I verified), and treat hit rate and MRR as the main numbers, recall as secondary.
- **Section labels are coarse and flatter the score.** A chunk from the right section but the wrong part counts as a hit.
- **Unanswerable questions** have no gold section; they are scored on the generation side (did it refuse?).
- **Multi-hop questions** need several sections together; score them as their own group.
- **Label sections, not chunks.** Chunk ids change whenever chunking changes; heading numbers do not. This is also why the heading-number vs file-number confusion matters.

### Ways to label (and how others do it)
| Method | A retrieved chunk is a hit if... | Trade-off |
|---|---|---|
| **Section** (our current idea) | its section number is in the gold set | Easy to write, stable across re-chunking, optimistic |
| **Evidence phrase** | its text contains a short exact phrase copied from the passage (e.g. "the mighty son of Pandu") | Strict, still stable across chunk sizes, more effort per question |
| **Both** (leaning towards) | report both numbers | The gap shows how generous the section label is |

How the wider field does it (from background knowledge, not freshly searched; verify before quoting publicly):
| Approach | How it works | Where it appears |
|---|---|---|
| Relevance judgments ("qrels") | A table of question, document id, relevance grade (for example 0 to 3), filled in by human assessors | TREC evaluations; benchmarks such as BEIR and MS MARCO |
| Document-level labels | The gold unit is a whole stable item: a help article, a support page, a contract clause | Most company RAG systems, because document ids survive re-chunking. **Our "section" is this.** |
| Answer-string matching | A passage is a hit if it contains the known answer text | Open-domain question answering; the original dense-retrieval (DPR) paper scored top-k accuracy this way. **Our evidence phrase is this.** |
| Span or evidence labels | The gold item is a highlighted span (character offsets); a chunk counts if it overlaps | Question-answering datasets, some chunking studies |
| Synthetic labels | A language model writes a question from a chosen chunk; that chunk is the gold | Quick bootstrapping |
| Judged by a model or by users | A language model, or click and feedback data, decides relevance | Production monitoring; reference-free tools such as Ragas |
Cautions: synthetic questions flatter retrieval because they share the chunk's wording and miss exactly the alias and lineage questions that matter here, so keep the set human-written. Model-judged relevance is useful but circular if the same model also generates answers.

### Generation metrics (a language model as judge)
- **Faithfulness:** every claim follows from the passages given, and each cited passage really supports its claim. This would have caught the bad Subhadra citation in Q3.
- **Answer relevance and correctness:** it answers the question and matches the expected answer.
- **Refusal accuracy:** it refuses exactly when it should.
- The judge should ideally be a different (preferably stronger) model than the generator; chosen when we build it. Later: compare my own implementation with the Ragas and DeepEval libraries, after checking they are current.
- **Fixed step (not optional): run Ragas against my own metrics.** After my generation metrics are baselined, run the same questions, answers and passages through Ragas with the same Gemini judge. Record a side-by-side table in `EXPERIMENTS.md` and read each disagreement to decide who was right. Add a "Ragas vs my own metrics" section here. Purpose: be able to explain, in interviews, how faithfulness is computed (split the answer into claims, check each against the passages), why a single judge is biased, and give a real example from our data where the two disagreed. DeepEval comes after Ragas if time allows. Check both libraries are current and work with Gemini first.

### Rules that keep the evaluation honest
- Write the set **before** looking at Phase 3 results, and **never edit it** to flatter them. New questions go in a clearly marked separate section.
- Mix the types: plain facts, alias pairs (the same question under different names), lineage and relation questions, multi-hop, unanswerable, ambiguous names. About 40 questions. Starting target: 10 / 8 (4 pairs) / 8 / 6 / 4 / 4.
- Q1 to Q8 in `QUESTION_LOG.md` are seeds, not part of the set.
- The questions are mine to write (I know what I want to ask); Claude finds the source sections and phrases and drafts expected answers, and I verify them against the text.

### Approaches to writing evaluation questions
| Approach | How it works | Strength | Weakness |
|---|---|---|---|
| Read and ask | A person reads sections and writes questions | Realistic wording | Slow; clusters on famous scenes |
| From structure | Section II lists the epic's events; use it as a checklist of episodes | Spreads questions across the book | Only headline events |
| From our failures | Q1 to Q8 and the problem map: aliases, lineage, multi-hop | Targets known weak spots | Biased towards what already broke |
| Same fact, different names | Take one verified fact and ask it once per name | Isolates the name problem exactly | Needs a fact in a known section |
| Model-written from chunks | A language model writes a question from a chunk | Fast, cheap | Reuses the chunk's wording so retrieval looks better than it is; chunk-bound labels; misses the alias problem |
| Real user questions | Collect what people ask | The truth | None exist yet |
Chosen: a blend of the first four. No model-written questions in the main set. Real questions are added later in a separate, marked file.

### Goals to keep in mind while writing questions
1. Check the answer exists in the Adi Parva first, and note the section(s) and a short evidence phrase before the question is final.
2. Write like someone who has not read the text; do not copy the passage's wording.
3. One question tests one thing, so a failure is diagnosable; tag every question with a type.
4. A difficulty ladder: easy (name and words match), medium (paraphrased), hard (aliases, lineage, multi-hop).
5. Pair the names: ask the same fact under different names so the alias problem becomes a number.
6. Spread across the book (early, middle, late) and include rarely mentioned facts (Ekalavya is in 2 sections, Kindama in 1).
7. No facts that need the rest of the epic; no trick questions unless tagged ambiguous.
8. Freeze the set and split it (below).
9. Be modest about size: with 36 questions one question is about 2.8 points, so only large differences count; report counts as well as percentages.

### The working / held-out split
**Problem:** over many Phase 3 experiments I will tend to keep changes that happen to suit these particular questions (for example special handling for exactly the Arjuna / Partha pairs). The score rises but the system has only learned the test, like a student who rehearses one exam paper.
**Fix:** split the set before experimenting. **Working set (24)** is used constantly: run after every change, failures studied. **Held-out set (12)** is locked: its failures are never read or tuned against, and it is run only at milestones (the baseline, the end of each phase). If a change helps both groups it is probably real; if only the working set, I have fitted the test.
**How it was drawn (fixed before any question was scored):**
- Held-out size fixed per type: 3 plain, 1 paraphrase, 2 alias (one pair), 1 spelling, 2 lineage, 2 multi-hop, 1 ambiguous.
- Name pairs always stay together, otherwise one half would teach me about the other.
- Units drawn at random within each type with a seeded generator; seeds tried in order 1, 2, 3...; the first seed giving 3 to 5 held-out questions in each third of the book was kept. Seed 1 worked: 4 early, 4 middle, 4 late.
- Frozen: `scripts/make_split.py` refuses to reassign unless forced; `--check` verifies it. Rule and seed recorded in `eval/split_info.json`.
**Cost:** only 12 held-out questions, so one question is about 8 points; it is a sanity check, not a precise score.
**Held-out ids:** R02, R04, R07, R09, R17, R18, R22, R24, R27, R29, R30, R35 (the text of every question is in `eval/retrieval_questions.csv`; what is hidden is the habit of studying their failures).

### The retrieval question set (36, in `eval/retrieval_questions.csv`)
| Type | Count | Held-out | What it tests |
|---|---|---|---|
| plain | 8 | 3 | the name and wording match the passage |
| paraphrase | 4 | 1 | the answer is asked without the passage's words or names |
| alias | 8 (4 pairs) | 2 | the same fact under different names (Arjuna / Partha, Sauti / Ugrasrava, Vyasa / Dwaipayana, Arjuna / Dhananjaya) |
| spelling | 2 | 1 | modern spelling vs the book's (Hidimba / Hidimva; Babhruvahana, not found in the text under that spelling) |
| lineage | 6 | 2 | parents and relations |
| multi-hop | 4 | 2 | several passages needed (Bhishma and Vichitravirya; Yudhishthira from Santanu; Astika and Vasuki; Yadu and Puru through Yayati) |
| ambiguous | 4 | 1 | names that mean more than one person (Krishna, Parikshit, Janamejaya) |
**Spread across the book** (early = Sections 1 to 79, middle = 80 to 158, late = 159 to 236): 12 / 14 / 10 questions; held-out 4 / 4 / 4.
**Correction made while balancing:** the first draft had only 5 of 36 questions in the early third (the snake-sacrifice parvas: Paushya, Pauloma, Astika), although that third is a third of the book. I replaced 10 questions (dropped: Ghatotkacha's parents, Yayati's old age, a duplicate Pandu's-curse paraphrase, the warned-snakes paraphrase, the Bhima / Vrikodara pair, Baka spelling, Vidura's father, Yayati's sons by Devayani, common ancestor; added: Sarama's curse, Parikshit's death, the snake-sacrifice paraphrase, the burning-lodging paraphrase, the Sauti / Ugrasrava pair, Hidimba spelling, Jaratkaru's marriage, Ruru's parents, Astika and Vasuki) and reworded one. Lesson: a set drawn from memory leans towards famous scenes; check the spread on purpose.
All section numbers in the file are **guesses until `gold_sections` is verified from the text**. Unanswerable questions are not in this set; they belong to the generation evaluation.

### Labelling the 36 questions (done)
**How:** for each question I searched the paragraphs, read the passages, chose the gold sections and short evidence phrases, and wrote the expected answer from the text. `scripts/verify_labels.py` then checks mechanically that every phrase appears word for word in a gold section **and** sits fully inside at least one chunk (chunks overlap by 200 characters, so a short phrase can never be cut in half by chunking). All 36 pass.
**Limit to remember:** the labels were written by Claude and checked by script; the project owner has not independently verified them (recorded in the CSV `status` column and `eval/README.md`). A wrong or missing label would show up as a strange retrieval result and must be handled under the "no edits to flatter results" rule.

**What reading the text changed (all before any scoring):**
| Finding | Effect |
|---|---|
| R07: Sarama cursed Janamejaya and his brothers, not only the brothers | question reworded |
| R26: the text names Drupada as the father and the children were born from the sacrificial fire; no mother is named in the way "parents" assumed | reworded to "Whose children were Dhrishtadyumna and Draupadi, and how were they born?" |
| R36: every later Janamejaya also descends from Puru, so "which Janamejaya descended from Puru" had two right answers | reworded to "Who was Janamejaya, the son of Puru?" |
| R06: I guessed Section 188; the contest condition is in 187 and the shot in 190 | gold corrected |
| R22: the book spells the name **Vabhruvahana**; "Babhruvahana" never occurs | a genuine spelling-variant test |
| R21: the text calls both the Rakshasa and his sister **Hidimva** (the question says Hidimba) | noted; spelling and same-name test in one |
| R02 Pandu's curse is restated in Section 95 | gold widened to include Section 95 |

**Discovery: the book contains summary passages that restate many answers.** Section 1 (the "I had no hope of success" list), Section 2 (the table of contents of the whole epic) and especially **Section 95** (one 6,000-character paragraph that retells the whole dynasty: Santanu, Bhishma, Vichitravirya, Dwaipayana's three sons, Pandu's curse and wives, Hidimva, Vaka, Draupadi, Subhadra, Parikshit, Janamejaya) answer many of our questions in a single paragraph. I added them to the gold sections wherever they truly state the answer, otherwise a correct chunk from a summary would count as a miss. Two consequences: (1) multi-hop questions R29 and R30 are partly "find the summary" tests; (2) retrieval may look better than it is simply because the summaries are easy targets. The retrospective should compare scores with and without the summary sections.
**Other label notes:** both halves of each name pair carry identical labels so the pair is a fair test; the real spread of the answers across the book is 13 early / 13 middle / 10 late, and the held-out set is still 4 / 4 / 4.

### How the retrieval evaluation runs, step by step
This is the plain-words flow behind every score. (Retrieval evaluation only; the language model is not called, so it costs nothing.)
1. **Take a question from the CSV.** The CSV also holds its answer key: the gold sections and the evidence phrases.
2. **Run the retriever.** It returns the top chunks for that question (we fetch 10 and use the top 5 for the headline number).
3. **Decide hit or miss for each chunk, in two ways:**
   - *Section check:* every chunk already carries the section number(s) it came from (stored when the chunks were built). It is a hit if one of them is a gold section.
   - *Phrase check:* the phrase is **not** taken from the chunk. It comes from the CSV. We do a plain text search for it inside the chunk's text. It is a hit if any evidence phrase appears word for word.
4. **Turn the hit/miss pattern into the question's scores** (hit at 5, first hit's rank, precision, recall, nDCG). Hit or miss is decided per chunk; the scores are per question.
5. **Average over all questions** in the group (working or held-out). Those averages are the baseline numbers.

**One real example, R03 "What did Drona ask Ekalavya to give him?"** The CSV says: gold section 134; phrase "I should like then to have the thumb of thy right hand".
| Rank | Chunk's section | Section hit? | Contains the phrase? |
|---|---|---|---|
| 1 | 134 | yes | yes |
| 2 | 168 | no | no |
| 3 | 133 | no | no |
| 4 | 133 | no | no |
| 5 | 134 | yes | yes |
Result for this question: hit@5 = 1; first hit at rank 1, so reciprocal rank = 1.0; precision@5 = 2/5 = 0.4.

**The generation evaluation (planned) is different:** it looks at the *answer* the model wrote. Question, then chunks, then the model's answer; then a judge compares the answer with the expected answer and with the chunks it was given (is every claim supported? is it correct? did it refuse when it should?). It needs a judge model, so it costs money.

### Retrieval evaluation: what was built
**Code:** `src/rag/metrics.py` (pure metric functions), `src/rag/eval_retrieval.py` (runs the retriever on the question set and scores it), `src/rag/textnorm.py` (shared text matching), `scripts/run_retrieval_eval.py` (command line), `tests/test_metrics.py` (18 checks, including the worked examples from the metrics table). No new libraries.
**How a question is scored:** retrieve 10 chunks; for each chunk decide hit or miss under two checks: **section** (touches a gold section) and **phrase** (contains an evidence phrase word for word). From those hit/miss flags compute hit rate, precision, recall, MRR and nDCG at k = 1, 3, 5, 10.
**Choices worth remembering:**
- **Recall** is the fraction of gold sections (section check) or evidence phrases (phrase check) that appear anywhere in the top k.
- **nDCG's "best possible ordering"** uses the number of relevant chunks that exist in the whole corpus (capped at k). For the section check a whole section holds many chunks, so the ideal is five hits and nDCG looks harsh (0.32); for the phrase check only one to three chunks qualify. nDCG therefore depends on the label definition; read hit@5 and MRR@5 first.
- **Summary variant:** `--exclude-summaries` drops Sections 1, 2 and 95 from the labels, to show how much of the score comes from those easy targets.
- **Held-out protection built into the tool:** the default run scores only the working set and prints per-question detail; held-out needs `--confirm-milestone "reason"`, prints aggregates only (no per-question, no per-type lines), and every run is appended to `eval/heldout_runs.log`.
- **Verified by hand:** I recomputed three questions (R14, R03, R19) from the raw retrieval and they matched the evaluator exactly.

### Retrieval baseline results (Phase 1 pipeline; full table in `EXPERIMENTS.md`)
| Set | Check | hit@5 | MRR@5 |
|---|---|---|---|
| Working (24) | section | 0.92 | 0.58 |
| Working (24) | **phrase (strict)** | **0.67** | **0.35** |
| Working, no summaries (22) | phrase | 0.50 | 0.28 |
| Held-out (12), one milestone run | phrase | 0.75 | 0.58 |

**What the numbers say** (from the working set, which I am allowed to study):
- **Right neighbourhood, wrong chunk.** The section check passes 92% but the phrase check only 67%: retrieval usually lands in the right section but not on the chunk that states the answer. Only 21% of questions have the answer chunk at rank 1.
- **The summary passages flatter the score.** Without Sections 1, 2 and 95, hit@5 falls from 0.92 to 0.77 (section) and 0.67 to 0.50 (phrase). Example: "How did Partha win Subhadra?" scored a hit only because the Section 1 summary came back; the real scene in Section 222 never did.
- **By type (phrase hit@5, working):** paraphrase 3/3, ambiguous 3/3, alias 4/6, plain 3/5, multi-hop 1/2, lineage **1/4** (MRR@5 only 0.06). "Who were X's parents?" questions retrieve narrative about X rather than the sentence that states the parentage.
- **Name pairs (the central challenge):** Arjuna rank 1 vs Partha rank 4 (and the Partha hit came from the summary); but Sauti rank 3 vs Ugrasrava rank 1 (the rarer name did better), and the Vyasa / Dwaipayana pair failed identically. With three pairs this shows the effect exists and is not uniform; it proves nothing about size.
- **Held-out is in the same range** as the working set (0.75 vs 0.67 phrase hit@5), which suggests the working-set result is not a fluke. With 12 questions the gap is within noise.
**Lessons:** (1) the strict check and the summary-free variant are the honest numbers; the generous ones are ceilings; (2) always report counts (16 of 24) next to rates; (3) a metric must be tested against hand calculation before its numbers are believed.

### Generation evaluation: what it is and how it runs (lesson written before the build)

Status: **built, calibrated and run: the judge is frozen (sections 6a to 6c) and the official working-set baseline is in section 6d. Held-out run not done yet.** Sections 1 to 3 below are updated to match what was built. Section 4 onward is the original pre-build lesson and is still to be refined. The worked examples are *illustrative*, not from a real run.

#### 1. What generation evaluation is, and how we do it
- **Concept:** retrieval evaluation asks "did we fetch the right passages?". Generation evaluation asks "given those passages, did the model write a good answer?". The two are scored separately so we know which half to fix.
- **How, in one line:** for each question we produce an answer with the real system, then grade it from several angles. Some grades are plain code. The rest come from a second model, the **judge**, which gets a narrow job, only the information that job needs, and must reply in a fixed format (JSON) so code can read the score.
- **Why a judge model at all:** answers are free text, so there is no exact-match check. A second model reads the answer and decides, the way a person would grade it. It uses language understanding, not a line-by-line text comparison, so borderline cases can flip. That is why it must be checked against a human (calibration).
- **Who is who:** the **generator** (`gemini-3.1-flash-lite`) writes the answers and is the thing being tested. The **judge** (`gemini-3.5-flash`) only grades them. Both are set in `config.py`; the judge's instructions are in `src/rag/judge.py`.
- **Questions:** the same 36 as retrieval (24 working, 12 held-out), plus 8 **unanswerable** ones (6 working, 2 held-out), in `eval/generation_questions.csv`. Every unanswerable question was scanned against the corpus to confirm the answer is absent.
- **Where the code is:** `src/rag/eval_generation.py` (scoring), `src/rag/judge.py` (the judge's jobs), `scripts/run_generation_eval.py` (the runner). Replies are cached on disk, so a rerun is free and a crashed run resumes.

#### 2. The two ways to run it
| Mode | Passages given to the generator | What a result tells us |
|---|---|---|
| **End-to-end** | What the real retriever returns (top 5) | The user-facing truth: retrieval and generation together |
| **Ideal context** (also called oracle retrieval) | The gold passage(s) handed over directly | The generator alone. A bad answer here is the generator's fault |

- **Reading the pair:** good in ideal context but bad end-to-end means fix retrieval. Bad in both means fix the prompt or model. The gap between them is the cost of imperfect retrieval.
- Only the passage-fetching step differs. Everything after it is identical.
- **Ideal context applies to answerable questions only.** An unanswerable question has no gold passage to hand over, so it appears in end-to-end mode only.
- **First reading from our baseline (working set, provisional):** correctness 0.81 end-to-end against 0.96 with ideal context. So most wrong answers come from retrieval, not the generator. Faithfulness and citation support did not improve with perfect passages, which pointed us at the generator and the judge itself, and led to calibration.
- The ideal-context idea exists in research as "oracle retrieval". Libraries do not ship it as a feature, so it is our own design choice.

#### 3. The metrics: what they mean, how they are calculated
**The three sources of input.** Every metric is built from some mix of these:
| Source | What it holds | Who sees it |
|---|---|---|
| **The label files** `eval/retrieval_questions.csv` and `eval/generation_questions.csv` | `question`, `expected_answer`, `evidence_phrases`, `gold_sections`, `type`, `split` | the evaluation code. The judge sees only `expected_answer` (for correctness). The generator sees only the `question`. |
| **The retriever** | the 5 passages found for the question (end-to-end) or the gold chunks (ideal context) | the generator, and the judge for faithfulness and citations |
| **The generator** | the answer text it wrote | the judge and the code checks. The answer is *not* from the CSV. |

**Metrics graded by the judge (an AI reads and decides)**
| Metric | Meaning | Judge sees (and from where) | Score |
|---|---|---|---|
| **Correctness** | Matches the expected answer | the **question** and **expected answer** (CSV) and the **generator's answer**. No passages, so fluent but wrong text cannot fool it. | 1 / 0.5 / 0 |
| **Faithfulness** | Every claim is backed by the retrieved text. Not "true in the world", but "the text says it" | two calls. A: the generator's answer only (list its single claims). B: the **5 passages** plus those **claims** (supported or not, with a quote). | supported claims / all claims |
| **Citation support** | Each `[n]` really backs the sentence it sits on | one **sentence** of the answer and **only the passage(s) it cites**. Code finds the sentences and markers. | backed sentences / cited sentences |
| **Relevance** | The answer addresses the question asked | the **question** (CSV) and the generator's answer | 1 / 0, refusals left out |

**How each judge metric becomes the final number**
Every judge metric is built in two steps.
1. **Score each answer on its own.** Each answer gets one number from 0 to 1.
2. **Add up those numbers and divide by the number of answers.** Each answer counts once, so a long answer carries the same weight as a short one.

| Metric | Step 1: the score of one answer | Step 2: add up, divide by | Final number (baseline, end-to-end, working set) |
|---|---|---|---|
| **Correctness** | the judge's verdict: 1, 0.5 or 0. A refusal on an answerable question is set to 0 by code. | the **24** answerable questions | **0.81**: 17 answers x 1 + 5 x 0.5 + 2 x 0 = 19.5, and 19.5 / 24 = 0.8125 |
| **Correctness, when it answered** | same verdicts | the **23** questions that were not refused | 19.5 / 23 = 0.848, shown as **0.85** |
| **Faithfulness** | supported claims / all claims **in that answer** (R21: 4 of 6 = 0.67) | the **23** answers that were given | **0.92**: 19 answers scored 1.0 and 4 scored lower (together 2.22), so the 23 scores add up to 21.22, and 21.22 / 23 = 0.922 |
| **Citation support** | backed cited sentences / all cited sentences **in that answer** (R10: 2 of 3 = 0.67) | the same **23** answers | **0.74**: 14 answers scored 1.0 and 9 scored lower (together 3.0), so the scores add up to 17.0, and 17.0 / 23 = 0.739 |
| **Relevance** | 1 if the answer tries to answer the question, else 0 | the 23 answered, answerable questions | 23 / 23 = **1.00** |

- **The 23 and the 24 count answers, not claims.** One answer with many claims is still one score in step 2. A small made-up example: if 22 answers scored 0.67 and one scored 0.90, the faithfulness is (22 x 0.67 + 0.90) / 23 = 15.64 / 23 = 0.68.
- **Where the 0.81 comes from:** of the 24 answerable questions, 17 were fully correct, 5 partly correct (worth half) and 2 scored zero. The two zeros are R25 (a refusal, because retrieval missed the Surya passage) and R05 (the answer said the passages did not say who set the fire).
- **Two correctness numbers:** 0.81 punishes refusals (R25 counts as 0); 0.85 shows how good the answers are when the system does answer. The gap between them is the cost of refusing.
- **Ideal context, same arithmetic:** 22 x 1 + 2 x 0.5 = 23, and 23 / 24 = 0.958, shown as **0.96**.
- **The alternative, pooling:** add up every claim from every answer and divide once (baseline faithfulness would be 65 of 71 = 0.915; citations 28 of 38 = 0.737). We use the per-answer average (the code is `summarise` in `src/rag/eval_generation.py`) so one long answer cannot dominate. Keep this choice fixed across experiments.
- **An average hides the spread.** When a number moves between experiments, check which answers changed.
- **Rounding:** the log prints two decimals, so 0.8125 appears as 0.81.

**Metrics computed by plain code (no AI)**
| Metric | Meaning | Input | How |
|---|---|---|---|
| **Gold text in the passages** | Did retrieval put the answer text in front of the model? | the **5 retrieved passages** and the **`evidence_phrases`** (CSV) | true if any phrase appears word for word (after normalising spaces and case) in any passage. Averaged over answerable questions. |
| **Invalid citations** | Did the answer cite a passage that does not exist? | the **generator's answer** and the **number of passages given** (5) | any `[n]` outside 1 to 5 is invalid. It is stored in each record. It is not a headline number, but such a sentence is scored "not backed" in citation support. |
| **Refusal accuracy** | Refuses exactly when it should | the generator's answer and whether the question is answerable (CSV) | the answer contains the exact refusal sentence ("The provided passages do not answer this question."). Gives a 2x2 table and the outcome labels (answered, correct refusal, false refusal from retrieval, false refusal from generation). |

**Generation metrics versus calibration metrics: two different questions**
| | Generation metrics (above) | Calibration metrics (section 6) |
|---|---|---|
| **Question answered** | How good is the RAG system's answer? | Can we trust the judge that produces those scores? |
| **What is compared** | the answer against the expected answer, or against the retrieved passages | the judge's verdicts against the owner's hand grades on the same answers |
| **Who produces the numbers** | the judge (and code) | the owner (human) and the judge, compared by `scripts/compare_calibration.py` |
| **Unit** | a score from 0 to 1 per answer, averaged | agreement: do the two verdicts match? Counted per answer or per sentence. |
| **Used for** | comparing experiments in Phase 3 | deciding whether the judge is allowed to score at all (bar about 80%) |
| **Rerun when** | every experiment | only if the judge's instructions change |

- **Industry view:** faithfulness, answer relevance, correctness against a reference answer and citation checks are standard generation metrics; Ragas and DeepEval offer versions of them, which is why a side-by-side comparison is planned. Checking an LLM judge against human grades is also standard practice, but the way we count agreement here is our own design, not a library function.
- **They connect in one direction:** calibration does not change the system's scores. It tells us how far to believe them.

**Rules the judge follows (frozen, fingerprint `2578221ecdd4`):**
- **Correctness:** full (1) = the key fact(s) of the expected answer are stated, including the cause when the expected answer has one (for "How did Parikshit die?" the curse is needed; "bitten by Takshaka" alone is partly right); partly (0.5) = right idea or right entity but a key part missing or hedged; no (0) = wrong, or a refusal on an answerable question.
- **Faithfulness and citations:** the passages are the only truth. A fact that is true in the story but not in the passages counts as unsupported. Two different names for one person match only when the passages show it; spelling variants of one name always match.
- **Refusals** are detected by code (the exact refusal sentence), not judged by the model.

**What the run prints, in plain terms:**
| Printed as | Meaning |
|---|---|
| correctness (refusals count 0) | average over all answerable questions, a refusal scores 0 |
| correctness (when it answered) | average over answers only, so it ignores refusals |
| faithfulness, citation support | averaged over the answers that have claims or cited sentences |
| relevance | refusals are left out |
| gold text was in the passages | share of answerable questions where retrieval put an evidence phrase in the top 5 |
| outcomes | answered, correct refusal, false refusal caused by retrieval, false refusal caused by generation |

**Reading them together:**
- Faithfulness high, correctness low: honest but wrong or incomplete. The passages usually lacked the answer, so look at retrieval.
- Correctness high, faithfulness low: right from the model's memory. Dangerous for this project, because the citations then mean nothing.
- Citation support low, faithfulness fine: the claims are true, but the `[n]` marks are misplaced.
- False refusals: split into retrieval-caused (ideal context answers) and generation-caused (even ideal context refuses).
- Correct refusals on unanswerable questions but false refusals on answerable ones: the model is too cautious, so tune the prompt, not the retriever.
- Faithfulness and citation support overlap (one unsupported claim can lower both) but are not the same. Faithfulness counts claims. Citation support asks whether the marker is honest.

**Worked example across four situations (illustrative):**
| Question | What happened | Faithful | Cites | Correct | Verdict |
|---|---|---|---|---|---|
| A. "Who was Bharata's father?" | Gold retrieved, "Dushyanta [2]" | 1/1 | 1/1 | 1 | all good |
| B. answerable, retrieval missed the gold | Model refuses | n/a | n/a | 0 | false refusal. Ideal context answers, so fault is **retrieval** |
| C. answerable, gold retrieved | Right answer plus one outside-knowledge claim and one misplaced `[3]` | 3/4 | 1/2 | 1 | correct but unfaithful. Same in ideal context, so fault is **generation** |
| D. unanswerable | Model refuses | n/a | n/a | n/a | correct refusal |

#### 4. How each mode worked in our first run, and the results
Both modes ran together (`python scripts/run_generation_eval.py --mode both --save baseline_working`) on the **working set**: 24 answerable and 6 unanswerable questions. Same generator (`gemini-3.1-flash-lite`), same judge (`gemini-3.5-flash`), same prompt. Only the passages handed to the generator differ.

**Mode 1, end-to-end (30 questions)**
- **Input:** the question; the real retriever's top 5 chunks (1,670 chunks, `bge-small-en-v1.5`, cosine similarity); the generator prompt asking for `[n]` citations.
- **Per question:** retrieve, generate, then code checks (is it the refusal sentence? do the evidence phrases appear in the five passages, giving a "gold text was in the passages" flag? do the `[n]` marks point at real passages?), then the judge scores correctness, relevance, faithfulness and citation support. A refusal on an answerable question scores correctness 0 and is labelled a retrieval fault if the gold text was missing, a generation fault otherwise.
- **Includes the 6 unanswerable questions**, to test refusal.

**Mode 2, ideal context (24 questions)**
- **Input:** the same prompt, but the five retrieved passages are replaced by the **gold chunks**: every chunk that contains at least one evidence phrase from the CSV, those matching most phrases first, at most 5, no padding. Retrieval is skipped, so "gold text found" is always yes.
- **Answerable questions only**, because an unanswerable question has no gold passage.

**Where the results are:** `eval/results/gen_baseline_working.json` has `config` (the setup), `summaries` (averages per mode) and `records` (per-question detail, with the judge's claim and citation verdicts). Raw replies are cached in `data/cache/gen_eval/` (not committed). The logged summary is in `EXPERIMENTS.md`.

**Results (provisional: scored with the judge's original instructions, before calibration)**
| Metric | End-to-end | Ideal context |
|---|---|---|
| Correctness (refusals count 0) | 0.81 | 0.96 |
| Faithfulness | 0.93 | 0.88 |
| Citation support | 0.83 | 0.75 |
| Relevance | 1.00 | 1.00 |
| Gold text in the passages | 0.67 | 1.00 |
| Correct refusals / false refusals | 6 of 6 / 1 of 24 | not applicable |

#### 5. What the results showed, and what led to calibration
**Observations**
1. **Retrieval is the main weakness.** Handing over the right passages lifted correctness from 0.81 to 0.96. In end-to-end mode the gold text reached the model in only 67% of questions. The one false refusal (R25, Karna's father) was a retrieval fault: the passage that names Surya never made the top 5.
2. **Refusal behaviour is healthy:** 6 of 6 unanswerable questions were refused, and 1 of 24 answerable ones was wrongly refused.
3. **Faithfulness and citation support did not improve with perfect passages; they got slightly worse** (0.93 to 0.88, 0.83 to 0.75). If these were simply a retrieval problem they should have risen. Something else was going on, and we could not tell whether the generator was over-claiming or the judge was being unreasonable.
4. **Some verdicts looked odd on a close read.** For example, a sentence naming "Parikshit" was marked not backed because the passage said "the king"; a correct answer using Dwaipayana was marked not backed because the passage said "Vyasa". Those are the many-names-for-one-person problem, now hitting the judge, not only the retriever.

**Why that led to calibration.** The judge is an AI grading another AI, and its scores steer every later experiment (chunking, embeddings, reranking). If it is miscalibrated we could keep a worse change or drop a better one without knowing. So before trusting the numbers we compare the judge with a human: the project owner grades a sample of answers blind (judge scores hidden), and we measure how often they agree. About 80% is our bar. The first sample was 12 answers; where they disagree we read both reasons and fix the judge's instructions, one change at a time. The calibration story and its fixes are written up next.

#### 6. Judge calibration, round 1
**Why we calibrate.** The judge is an AI grading another AI, and its scores steer every later experiment (chunking, embeddings, reranking). If it is miscalibrated we could keep a worse change or drop a better one without noticing. In the baseline, faithfulness and citation support got slightly worse with perfect passages, which made us unsure the judge was doing a good job. So before trusting any score, the project owner grades a sample blind and we measure how often owner and judge agree. Our bar is about 80%.

**What we did in the first iteration**
1. **Sample:** 12 answers from the end-to-end baseline, picked by fixed rules (a wrongful refusal, correct refusals, answers the judge scored low or partial, right answers with weak faithfulness, weak citations, and a few clean ones), so the sample is not all easy cases. Items: R25, G01, G02, R05, R08, R12, R21, R20, R01, R03, R06, R10.
2. **Blind grading:** the owner filled in a form (`eval/calibration_form.html`, same content as `eval/calibration_sheet.md`) showing the question, expected answer, the system's answer split into sentences, and the five passages. The judge's scores were not shown; they were saved separately in `eval/results/calibration_key.json`.
3. **Grading standards:** *Correct?* is judged against the expected answer, using the owner's knowledge of the text. *Supported?* and *Citation ok?* use **only the passages shown**; a fact that is true but not in the passages counts as not supported.
4. **Comparison:** `scripts/compare_calibration.py` reduces both sides to something that can be matched and counts agreement. The owner's blind grades are kept unchanged in `eval/calibration_grades.md`.

#### Calibration measures: what each means and how it is calculated
Calibration compares the owner's blind grades with the judge's scores on the same 12 answers. There are three comparisons. Each reduces both sides to something that can be matched.

**1. Correct? (does the answer match the expected answer)**
- The owner answers yes, partly or no. This becomes 1, 0.5 or 0.
- The judge gives its own 1, 0.5 or 0 for the same answer.
- Agreement = the two numbers are exactly equal. Agreement rate = matches / items.
- A correct refusal on an unanswerable question counts as agreement when the owner said yes.
- **Calibration 1: 8 of 12 (67%).**
- Example: R05. The owner said partly (0.5) and the judge gave 0, so they disagree. R01. Both said 1, so they agree.
- The four disagreements: R25 (owner partly, judge 0), R05 (owner partly, judge 0), R08 (owner yes, judge 0.5), R12 (owner no, judge 0.5).

**2. Supported? (is every claim in the answer backed by the retrieved passages)**
- The owner graded each *sentence* of the answer, yes or no, using only the passages.
- The judge works on *claims*, not sentences. It splits the answer into single claims on its own, which the owner never saw. One sentence can hold several claims, so the counts differ (R21: 3 sentences, 6 claims).
- The judge's faithfulness score = supported claims / all claims.
- Each side is reduced to one verdict per answer:
  - "all supported": every owner sentence is yes, or the judge's faithfulness is exactly 1.0.
  - "not all supported": at least one owner sentence is no, or the judge's faithfulness is below 1.0.
- Agreement = the two verdicts match. The fractions are not compared (a judge score of 0.67 and of 0.0 are both "not all supported").
- Refusals are left out because the judge does not score faithfulness for them. That is why the denominator is 9, not 12.
- **Calibration 1: 8 of 9 (89%).**
- Example: R21. The owner marked sentence 3 no, and the judge's faithfulness was 0.67. Both say "not all supported", so they agree. R12 was the mismatch: the owner marked every sentence yes, but the judge scored faithfulness 0.0.

**3. Citations ok? (does the cited passage back the sentence)**
- Only sentences that carry a [n] marker are graded. The owner marked each yes or no.
- Each owner sentence is lined up, in order, with the judge's verdict on the same sentence, backed or not backed.
- Agreement = both say backed, or both say not backed. This is counted one sentence at a time.
- **Calibration 1: 11 of 14 sentences (79%).**
- Example: R08. The owner said backed and the judge said not backed (the passage says "the king", the answer says "Parikshit"). R20 differed the same way (Vyasa vs Dwaipayana). R10 sentence 3 was the third mismatch.

**Faithfulness vs "all sentences supported"**
- Faithfulness is the judge's own score, supported claims / all claims.
- "All sentences supported" is the yes/no comparison used here to check the judge's faithfulness against the owner's sentence grades.

**Notes** the owner writes on each item are not scored. They are read to understand why the two sides disagreed.

#### 6a. Calibration 1: what we saw, and the judge fixes that followed
**Result (original judge, owner's blind grades):** correctness 8 of 12 (67%), all-supported 8 of 9 (89%), citations 11 of 14 (79%). The worry that the judge was unreliable on faithfulness turned out to be mostly unfounded: it was right to flag R21's marriage sentence (the owner agreed). The problems were elsewhere.

**What we saw**
1. **Names (R08, R20):** the judge marked citations "not backed" because the passage said "the king" or "the Rishi / Vyasa" and the answer said "Parikshit" or "Dwaipayana". The owner had marked them backed using knowledge of the story. This is the *many names for one person* problem, now hitting the judge. For R08 it is worse than it looks: the cited passage mentions "Parikshita" only as the *son* ruling later, a different person, so the passages never name the dying king (the *same name, different people* trap).
2. **R12, the judge contradicted itself:** the claim check said the claims were unsupported (no evidence quoted) while the citation check, on the same passage, said the passage "explicitly states" them. Two jobs seeing different slices of the same text can disagree.
3. **Correctness (R25, R05, R08, R12):** the disagreements were about partial answers. Our rubric (full, partly, no) had never been written down precisely. The owner settled it: *full* = the key facts of the expected answer, including the cause when the expected answer has one (for "How did Parikshit die?" the curse is needed); *partly* = right idea or entity but a key part missing or hedged; *no* = wrong, or a refusal on an answerable question. That matches what the judge already did, so the judge's correctness instructions were not changed.
4. **R10, a lesson in standards:** the judge rejected "the vow was taken so he would have no children who could claim the throne". The passage states the vow, not its purpose. True in the story, not in the passage. The owner agreed the judge was right. A model need not repeat a passage word for word, but a purpose or reason added on top of the stated fact goes past "directly implied".
5. **The owner's retrieval notes (kept for Phase 3):** the right section was often retrieved with the wrong paragraph (R05, R08, R12); R25's top-1 chunk was irrelevant; chunk boundaries cut off the key line (R20, R01).

**The fixes (only the "Names" rule in `src/rag/judge.py` changed; one variable at a time; the same 12 cached answers re-scored each time)**
| Fix | Change | Why |
|---|---|---|
| **1** | Names rule: different names of one person match when the passage makes it clear or the alias is well known | R08, R20 |
| **1b** (owner's decision) | Names match **only when the passages show it**; no outside knowledge | keeps "supported" meaning "the retrieved text shows it"; alias gaps become visible retrieval gaps for Phase 3 |
| **1c** | Spelling variants of one name always match (Hidimba / Hidimva) | 1b wrongly flagged R21; spelling is transliteration, not outside knowledge |

| Judge version | Correctness | All supported | Citations |
|---|---|---|---|
| Original | 67% | 89% | 79% |
| Fix 1 | 67% | 78% | 93% |
| Fix 1b | 92% | 78% | 79% |
| **Fix 1c** | **92%** | **89%** | **100%** |

*Caution:* the owner's grades were amended along the way (R25, R08, R12 correctness; R10 sentence 3; R08 and R20 citations), each time after seeing the judge's reason and with the blind originals kept (`eval/calibration_grades.md` vs `eval/calibration_grades_amended.md`). So this table is a consistency check, not independent evidence, and the columns are not strictly comparable. Also, the same answer's faithfulness flipped between 1.0, 0.75 and 1.0 (R10) just from rewording the instructions, so a single-item flip is noise.

#### 6b. Calibration 2: the independent test
**Setup:** 8 fresh answers not used in round 1 (R26, R31, R34, R36, R11, R13, G04, R14), picked by fixed rules in `scripts/pick_round2.py` (judge-flagged answers first, then clean ones, plus one refusal). The judge was fix 1c and was **not tuned on these**. The owner graded blind from `eval/calibration_sheet_round2.md`; grades in `eval/calibration_grades_round2.md`.

**Result before any amendment:** correctness 5 of 8 (62%), all-supported 6 of 7 (86%), citations 11 of 13 (85%). Item 1 citations were left as "?" and excluded. If correctness is reduced to *acceptable (yes or partly) vs wrong (no)*, agreement is 8 of 8 in round 2 and 19 of 20 across both rounds.

**What we saw**
- **Correctness, the "key fact" boundary, mixed direction:** R13 and R14 (owner partly because the Yadava girl and the chariot were missing; judge 1.0 because "forcible seizure" is the key fact) and R34 (owner yes; judge 0.5 for omitting that Vyasa composed the Mahabharata). The expected answers hold several facts and nothing marks which is *the* key fact, so a 3-level score is inherently fuzzy.
- **Citation strictness on small descriptors:** R36 ("not stated that he was a monarch") and R11 ("not stated that Parikshit was a king"). The judge's rule that *everything* in the sentence must be backed is stricter than a human reader.
- **R31, the judge was right and the owner reconsidered:** the claim check passed because passage 5 names Astika and his birth to the snakes' sister; the citation check, seeing only the cited passage [3], marked it not backed. Both are correct: the claim holds across the five passages, but the cited passage alone does not back it.
- **R34 sentence 2** ("son of the mother of Vichitravirya"): true in the story, but no shown passage names Vichitravirya's mother. The sentence that does was not retrieved.

**Owner amendments after seeing the reasons:** R13 and R14 partly to yes (the owner had compared with the longer expected answer); R31 Supported to yes, citations stay no. R36, R11 and R34 left as disagreements. **After amendment:** correctness 7 of 8 (88%), all-supported 7 of 7 (100%), citations 11 of 13 (85%).

#### 6c. Decision: freeze the judge
- Agreement is above the 80% bar on all three measures across both rounds, with the known limits listed above (citation check fussy about minor descriptors; "key fact" is a judgement call; R05 correctness and R12 faithfulness unresolved).
- We did **not** tune the judge on round 2, to keep it an independent test. Fixing round 2's items would require a round 3 to verify.
- Why a stable imperfect judge is acceptable: in Phase 3 we compare experiments scored by the *same* judge, so a constant bias cancels out. What breaks a comparison is changing the judge mid-way.
- **Mechanism:** the judge's instructions have a fingerprint (`2578221ecdd4`, `JUDGE_FROZEN_FINGERPRINT` in `config.py`). Every run records its own fingerprint and warns if it differs. Do not change the judge without a new calibration.

**Lessons from calibration**
- Define the standard before grading: *Correct?* is against the expected answer, while *Supported?* and *Citations* use only the passages. Mixing them was the root of most disagreements.
- A judge needs explicit handling of names: aliases (only if the passages show it), spelling variants (always), and different people with one name (never merge).
- Multi-job judges can contradict themselves because each job sees a different slice. Compare their reasons before blaming either.
- Never let the human grade drift toward the judge unrecorded: keep blind originals and log every amendment with its reason.
- Do not tune on the test you use to validate. Keep one set untouched.

#### 6d. The official baseline (frozen judge, working set)
`python scripts/run_generation_eval.py --mode both --save baseline_working_frozen` → `eval/results/gen_baseline_working_frozen.json`. Generator answers came from the cache (same prompts), so only the judge scores changed. Cost about $1.57.

| Metric | End-to-end (30 questions) | Ideal context (24) |
|---|---|---|
| Correctness (refusals count 0) | 0.81 | 0.96 |
| Faithfulness | 0.92 | 0.82 |
| Citation support | 0.74 | 0.71 |
| Relevance | 1.00 | 1.00 |
| Gold text in the passages | 0.67 | 1.00 |
| Correct refusals / false refusals | 6 of 6 / 1 of 24 | not applicable |

**Versus the provisional run:** correctness and relevance identical; faithfulness 0.93 to 0.92 and 0.88 to 0.82; citation support 0.83 to 0.74 and 0.75 to 0.71. The citation drop is the passages-only name rule doing its job.

**By question type (correctness / faithfulness)**
| Type | n | End-to-end | Ideal context |
|---|---|---|---|
| plain | 5 | 0.70 / 1.00 | 0.80 / 0.93 |
| paraphrase | 3 | 0.83 / 0.58 | 1.00 / 0.61 |
| alias | 6 | 1.00 / 1.00 | 1.00 / 0.75 |
| spelling | 1 | 1.00 / 0.67 | 1.00 / 1.00 |
| lineage | 4 | 0.62 / 1.00 (1 refusal) | 1.00 / 1.00 |
| multihop | 2 | 1.00 / 1.00 | 1.00 / 1.00 |
| ambiguous | 3 | 0.67 / 0.93 | 1.00 / 0.58 |

**Observations**
1. **Retrieval is the main weakness.** With the gold passages correctness rises from 0.81 to 0.96; end-to-end the gold text reached the model in only 67% of questions. Lineage questions suffer most (0.62 against 1.00); the one false refusal (R25, Karna's father) was a retrieval fault.
2. **Refusal behaviour is healthy:** 6 of 6 unanswerable questions refused, 1 of 24 answerable wrongly refused.
3. **Faithfulness is lower with perfect passages (0.92 to 0.82),** concentrated in paraphrase and ambiguous questions. This is not explained yet. Untested hypotheses: with only the gold chunks the model adds claims beyond them; the judge's claim splitting is stricter on longer, richer answers; the name rule bites harder when the answer uses different names from the gold chunk. To be investigated in Phase 3, not assumed.
4. **Citation support is the weakest metric (0.74 and 0.71).** Part of it is genuine (citations pointing at a passage that holds only part of the sentence), part is the judge's strictness about small descriptors. Read it as a relative measure across experiments, not as an absolute quality score.
5. **From the end-user view, answers are reasonably good** (owner's reading across both calibration rounds); most failures are missing facts caused by retrieval, not invented ones.

**Phase 3 notes carried from calibration:** right section but wrong paragraph; irrelevant top-1 chunks; key lines cut by chunk boundaries (R20, R01, R26 "And from Drupada wa", and the Satyavati sentence missing for R34); name traps that retrieval must handle (Parikshit vs Parikshita; Vyasa vs Dwaipayana; Hidimba vs Hidimva).


#### 6e. Held-out generation baseline (run once)
Run once with the frozen judge, aggregates only (the held-out set is never inspected question by question). Results, next to the working set:

| Metric | Held-out end-to-end | Held-out ideal | Working end-to-end | Working ideal |
|---|---|---|---|---|
| Correctness (refusals count 0) | 0.67 | 0.92 | 0.81 | 0.96 |
| Correctness when it answered | 0.89 | 1.00 | 0.85 | 0.96 |
| Faithfulness | 0.89 | 0.97 | 0.92 | 0.82 |
| Citation support | 0.85 | 0.86 | 0.74 | 0.71 |
| Gold text in the passages | 0.75 | 1.00 | 0.67 | 1.00 |
| False refusals | 3 of 12 | 1 of 12 | 1 of 24 | 0 of 24 |

**Observations**
- **The answers given are good** (correctness when it answered 0.89 end-to-end and 1.00 with gold passages). The lower headline number (0.67) comes from **false refusals**: 3 of 12 end-to-end, and 1 of 12 even when the gold passages were supplied. Retrieval was no worse than on the working set, so this is the generator being over-cautious ("The provided passages do not answer this question") on a few questions it could answer. It is a candidate for the Phase 3 stage on "I don't know" handling.
- **Retrieval-limited correctness generalises:** ideal context beats end-to-end in both sets. The 2 unanswerable questions were both refused correctly.
- **The faithfulness dip with gold passages did not repeat** (0.97 here against 0.82 on the working set), so the dip is probably question-specific. Keep it as an open question, not a finding.
- **Caveat:** 12 questions means one question moves a score by 8 points. Use the held-out numbers to check direction, not size. Do not tune against its failures; it is rerun only at milestones with `--confirm-milestone`.

#### 7. How a run works, shown on one real question: R01 "Who was Sakuntala's mother?"
Stored label: gold sections 72 and 74; evidence phrases "the Rishi begat on Menaka a daughter named Sakuntala" and "the lewd Menaka is thy mother"; expected answer "Menaka, the celestial Apsara (her father was the sage Viswamitra)."

**7.1 The input part**
- `eval/retrieval_questions.csv` (the 36; **never edited** for this): `question`, `expected_answer` (the truth for correctness), `gold_sections` and `evidence_phrases` (which chunks to hand over in ideal-context mode, and the "gold found" flag in end-to-end mode), `type` and `split` (grouping, working or held-out protection).
- **`eval/generation_questions.csv` (planned, does not exist yet):** the ~8 unanswerable questions: `answerable` = no, no gold section, expected result is a refusal, plus a note that a corpus scan confirmed the answer is absent.
- **Why unanswerable questions are needed:** all 36 have answers, so we could only test how well the model answers, never whether it knows **when not to**. A model that always answers (and invents facts when the passages say nothing) would look fine on the 36. A model that refuses too easily would show only on answerable ones. Unanswerable questions are the only way to measure refusal accuracy and catch hallucination. For the lineage project, a made-up parentage is worse than "I don't know".
- **Candidate types (none verified):** later events from other parvas; false premises; details the book never states; things outside the text.
- **The catch:** the book's summary passages (Sections 1, 2, 95) mention events from the whole epic, so a "later events" question may be answerable after all. Each one needs a corpus scan before it counts.
- **System under test:** chunks, embedding cache and retriever (end-to-end passages); generator settings from `config.py` (gemini-3.1-flash-lite, temperature 0, top 5) and the system prompt in `src/rag/generation.py`.
- **The judge (new):** model name in `config.py` (`gemini-3.5-flash`), plus one fixed instruction per job in `src/rag/judge.py`: correctness, faithfulness, citation support, relevance. Each says what to look at, what to ignore, and the exact reply format.
- **Calibration set (new):** about 12 answers the user grades by hand, used only to check the judge.
- **Access:** `GEMINI_API_KEY` in the environment (never printed or committed).
- **Output:** one saved result file per run in `eval/results/`, with the answer, judge replies and scores per question.
- **Size of a run:** about 44 questions x 2 modes x 4 judge jobs gives roughly 350 to 500 judge calls (the faithfulness and citation jobs scale with answer length). Check the price first.

**7.2 The steps that do NOT use the judge (plain code)**
1. **Load the question.** Keep the question and expected answer. Gold sections and phrases are used only to see whether retrieval found the right text. The generator never sees any label.
2. **Retrieve** the top 5 chunks (end-to-end). Also check by string match whether they contain the evidence phrases, giving a "gold found: yes or no" flag. No model involved. Needed later to explain failures.
3. **Generate** with the real prompt and `gemini-3.1-flash-lite`. This is the **generator**, the model being tested, not the judge. Illustrative answer: *"Sakuntala's mother was Menaka, an Apsara sent by Indra to disturb Viswamitra's penance [2]. She was born to them and left in the forest [2]."*
4. **Cheap checks.** Did the answer contain the exact refusal sentence ("The provided passages do not answer this question.")? Does every `[n]` point at an existing passage (the existing `check_citations`)? Code does everything it can before we pay for a model call.
5. Later: **save** one record per question, then **average** by group (answerable or not, type, working or held-out) and compare the two modes.

**7.3 The steps that use the judge**
The judge is called only after the generator has answered, and only for work code cannot do ("is this claim supported?"). Four separate calls, each a fresh conversation with only the slice it needs.

*Assumption for this example: passage [2] says Menaka was sent by Indra, that Viswamitra and Menaka had a daughter, and that she was left in the forest. It never uses the word "Apsara".*

1. **Correctness.** Sees question, expected answer, generated answer. Replies: score 1, reason "names Menaka as mother, mentions Viswamitra". Score used as is; the metric is the average of these.
2. **Faithfulness.** Stage A: from the answer alone, list the claims: (1) mother was Menaka, (2) Menaka was an Apsara, (3) Indra sent her to disturb the penance, (4) born to Menaka and Viswamitra, (5) left in the forest. Stage B: sees passages plus claims, marks each supported or not, with the sentence relied on. Claims 1, 3, 4, 5 supported; claim 2 **not supported** (the word is nowhere in the passages). Score 4/5 = **0.8**. This is how "right from memory" is caught: claim 2 may be true, but the text does not say it.
3. **Citation support.** Code splits the answer into sentences and finds each `[n]`. Each sentence goes to the judge with only its cited passage. Sentence 1 (cites [2], contains "Apsara"): **no**. Sentence 2: yes. The rule given to the judge: a sentence counts as backed only if everything in it is backed. Score 1/2 = **0.5**.
4. **Relevance.** Sees question and answer only. Yes, score 1. Refusals are skipped ("I don't know" is not irrelevant, just not an answer).

**Saved record for R01:** correctness 1; faithfulness 0.8 (claim 2 flagged); citation support 0.5 (sentence 1 flagged); relevance 1; not refused and answerable, so fine. Reading: right and relevant, but one outside fact sneaked in and the first citation overreaches. A plain "is it correct?" check would miss exactly this.

**7.4 How does the judge know what is right? (a question the user asked)**
The judge does **not** decide from its own knowledge and does **not** write an answer of its own. It compares the generator's answer with something we hand it:
| Check | The "truth" given to the judge | Source |
|---|---|---|
| Correctness | the expected answer | our label (Claude-written, script-checked); the only place real-world truth enters |
| Faithfulness | the five passages | retrieved text: "does the text say this", not "is it true" |
| Citation support | the one cited passage | same idea, narrower slice |
| Relevance | nothing but the question | needs language understanding, not facts |
| Refusal | no judge | string match in code |

- **Risk: the judge's pre-trained knowledge.** It knows the Mahabharata, so it can be too generous (knows Menaka is an Apsara, marks the claim supported although the passages do not say it) or too harsh (remembers a different version of the story and disagrees with our expected answer).
- **Reducing it:** (1) instructions say use only the material given; (2) the narrowest slice per call; (3) calibration on about 12 answers the user grades, to expose disagreement.
- **Why not let the judge write its own reference answer:** a second error source we cannot check. Our written expected answers are fixed, so any disagreement can be traced.

**7.5 Keeping the judge honest**
- Calibration: agreement with the user under about 80% means fix the judge instructions before trusting any score.
- Same-vendor bias: a Gemini judge may be generous to Gemini answers. Ragas gives a second opinion later.
- Fixed reply format (JSON) so scores are read by code, not guessed from prose.
- Judge instructions are frozen once calibrated. Changing them mid-experiment breaks comparisons.

#### Alternatives: how other RAG projects do it
- **Same everywhere:** the judge recipe (narrow job, right slice, structured reply); faithfulness by splitting into claims (Ragas, DeepEval, TruLens do essentially this, from memory, to be confirmed at the Ragas step); cheap checks in code; averaging by group.
- **Reference-based vs reference-free:** we check correctness against expected answers we wrote (more careful, costs labelling). Many teams cannot afford that and use reference-free metrics (faithfulness, relevance) plus correctness on a small set.
- **Answer relevance:** in Ragas, as remembered, it generates questions from the answer and compares them with the original by embedding similarity, not a direct rating. Ours is simpler and more transparent. Confirm when we run Ragas.
- **Citation support:** less common in general libraries. Research benchmarks for cited answers (for example ALCE) measure it. We need it because lineage claims must be traceable.
- **Pairwise judging:** "which of these two answers is better?" is often more reliable for comparing versions. Ours scores single answers, which fits one-change-at-a-time.
- **Cheaper faithfulness checkers:** small trained natural-language-inference models instead of a big LLM judge.
- **Production monitoring:** sampling live traffic and user feedback. Phase 6.

#### Gotchas and open design choices
- Whether faithfulness Stage A and B are two calls (more reliable, slower) or one.
- Whether the citation judge gives yes/no or yes/partly/no.
- Judge pre-trained knowledge leaking in (7.4).
- Unanswerable questions can be answerable through the summary passages, so scan first (7.1).
- Unanswerable questions are drafted by Claude and must be reviewed by the user.
- **Free-tier quota (found while building):** the Gemini key is on the free tier, which allowed only 20 requests per day for the judge model (error 429, "limit: 20", retry in about 13 hours). A full run needs roughly 400 or more judge calls, so the free tier cannot carry this evaluation. The error named `gemini-3.6-flash` although we asked for `gemini-3.5-flash`; unexplained.
- **Capacity errors (503 "high demand"):** common on both the generator and the judge model; a single call once stayed unavailable for about four minutes. The runner now waits longer between retries (`EVAL_RETRY_WAITS` in `config.py`), and cached replies make a crashed run resumable.
- **Thinking tokens:** the judge model spends several times more thinking tokens than visible output (3 trial calls: 78 output, 410 thinking), and thinking is billed as output. Costs are higher than the visible reply suggests.
- **Alias trap in the absence scan:** "Krishna" is also one of Draupadi's own names ("born Krishna (Draupadi)", Section 63), so searching for Krishna-related text finds Draupadi paragraphs. Use Vasudeva, Kesava, Madhava for the god.

### Decisions
Made: Claude drafts the questions and the user reviews them; the working / held-out split (24 / 12); approaches and goals above. Assumed unless the user objects: label by section **and** evidence phrase (both columns exist in the file). Done since: gold labels and evidence phrases for all 36 (above). Still open: whether the user adds questions of their own (a quarter of the set in their own words would be ideal; they would go in the separate "added" file).

---

## Phase 2 retrospective (final)

**Rule (also in `CLAUDE.md`):** at the end of every phase I write what worked, what did not, how it compares with standard RAG practice, and what it means for the next phase.

### Verdict
**Phase 2 is complete as a measurement phase, with one planned step moved.** We can now score the baseline in two separate halves (retrieval and generation), with a judge that was checked against my own grading and then frozen. The baseline numbers are recorded in `EXPERIMENTS.md` and are the reference for every Phase 3 change. **Moved to Phase 3 (the owner's decision):** the Ragas side-by-side comparison. The original plan said to implement the metrics myself first and then compare with Ragas or DeepEval; the first half is done, the comparison now runs alongside the Phase 3 improvements.

### What we built
| Part | What | Where |
|---|---|---|
| Question set | 36 labelled answerable questions (24 working, 12 held-out, frozen split) plus 8 unanswerable (6 working, 2 held-out, corpus-scanned) | `eval/retrieval_questions.csv`, `eval/generation_questions.csv`, `eval/README.md` |
| Retrieval metrics | hit@k, precision, recall, MRR, nDCG; strict phrase check and generous section check; with and without summary passages | `src/rag/metrics.py`, `scripts/run_retrieval_eval.py` |
| Generation metrics | correctness, faithfulness, citation support, relevance, refusal accuracy; two modes (end-to-end, ideal context) | `src/rag/eval_generation.py`, `src/rag/judge.py`, `scripts/run_generation_eval.py` |
| Judge | `gemini-3.5-flash`, narrow jobs, JSON replies, calibrated and frozen (fingerprint `2578221ecdd4`) | `src/rag/judge.py`, `config.py` |
| Calibration tooling | blind sheets and forms, a picker with fixed rules, a comparison script | `scripts/make_calibration_*.py`, `scripts/pick_round2.py`, `scripts/compare_calibration.py`, `eval/calibration_*` |
| Safeguards | held-out locked behind `--confirm-milestone` and logged; disk cache of model replies; judge fingerprint recorded in every run; 28 generation-evaluation tests | `eval/heldout_runs.log`, `data/cache/gen_eval/` |

### The baseline in numbers (Phase 1 pipeline, nothing tuned)
| | Working set | Held-out |
|---|---|---|
| Retrieval: hit@5, strict phrase | 0.67 (16 of 24) | 0.75 (9 of 12) |
| Retrieval: MRR@5, strict phrase | 0.35 | 0.58 |
| Correctness, end-to-end | 0.81 | 0.67 |
| Correctness, ideal context | 0.96 | 0.92 |
| Faithfulness, end-to-end / ideal | 0.92 / 0.82 | 0.89 / 0.97 |
| Citation support, end-to-end / ideal | 0.74 / 0.71 | 0.85 / 0.86 |
| False refusals, end-to-end | 1 of 24 | 3 of 12 |
| Correct refusals (unanswerable) | 6 of 6 | 2 of 2 |

### What worked
- **Separating retrieval from generation, and the two modes.** Comparing end-to-end with ideal context located the problem: correctness jumps from 0.81 to 0.96 (working) and 0.67 to 0.92 (held-out) when the right passages are supplied. Without this split, a retrieval miss would have looked like a "correct refusal".
- **Checking the judge before trusting it.** Two calibration rounds with blind grading caught real judge problems (name handling, a self-contradiction on R12) and showed the judge was mostly right on faithfulness. Keeping the blind originals and logging every amendment kept the evidence honest.
- **Keeping one test untouched.** Round 2 was graded on answers the judge was never tuned on, and we did not tune on it afterwards.
- **Freezing the judge with a fingerprint,** so Phase 3 comparisons cannot silently change the ruler.
- **The held-out protection.** Held-out run once, aggregates only, logged; no failure inspected.
- **Caching every model reply,** so re-scoring the same 12 answers after each judge fix cost cents and reruns resumed after crashes.
- **Script checks on every label** and recomputing metrics by hand before believing them.
- **Reading the data.** The summary passages (Sections 1, 2, 95) act as magnets for retrieval; spotting this early led to reporting every number with and without them.

### What did not work, or surprised us
- **The judge needed more care than the pipeline.** Most of the effort went into making the judge's standard explicit, not into building it.
- **A 3-level correctness score is fuzzy.** Expected answers hold several facts and nothing marks which is "the key fact" (R13/R14 against R34 pulled in opposite directions). Reduced to acceptable-vs-wrong, agreement was 19 of 20 across both rounds; on the 3-level scale it was 62% in round 2 before amendments.
- **My own grades drifted toward the judge.** Several of the owner's grades were amended after seeing the judge's reasons. Each was logged, but the agreement figures from round 1 are a consistency check, not independent proof.
- **Judge variance is real.** The same answer's faithfulness flipped 1.0, 0.75, 1.0 (R10) from rewording alone. Single-item flips are noise.
- **Small sets.** One held-out question is 8 points. Use held-out for direction, not size.
- **Labels have one author** (Claude, script-checked, delegated by the owner), so they reflect that author's view.
- **Unexplained:** on the working set, faithfulness and citation support were *lower* with perfect passages (0.92 to 0.82, 0.74 to 0.71). The held-out set did not repeat the faithfulness dip (0.89 to 0.97). Not investigated.

### Findings that shape Phase 3
1. **Retrieval is the bottleneck.** Gold text reached the model in only 67% (working) and 75% (held-out) of questions. Lineage questions suffer most (correctness 0.62 end-to-end against 1.00 with gold passages).
2. **Concrete retrieval failures found by hand** (from the owner's calibration notes): right section but wrong paragraph (R05, R08, R12); irrelevant top-1 chunk (R25); chunk boundaries cutting the key line (R20, R01, R26 "And from Drupada wa", the sentence naming Satyavati for R34).
3. **Name traps the system must handle:** Parikshit vs Parikshita (R08), Vyasa vs Dwaipayana (R20), Hidimba vs Hidimva (R21), "the king" without a name.
4. **Over-cautious refusing:** 3 of 12 false refusals end-to-end on held-out, and 1 of 12 even with the gold passages.
5. **Healthy where it matters:** every unanswerable question (8 of 8 across both sets) was correctly refused, and answers that were given were mostly good (correctness when answered 0.85 working, 0.89 held-out).

### Mistakes along the way (and the lesson from each)
- I described the calibration set as if it existed when no file or script had produced it yet. **Lesson:** say "planned, not built" plainly.
- The round 2 form links did not open for the owner and the HTML preview would not render. **Lesson:** have a plain-text fallback ready when sharing a form.
- `scripts/rebuild_all.sh` aborted because of a `| head` pipe under `set -e`. **Lesson:** a pipe that closes early is a failure in strict shells.
- My first rewrite of a `LEARNING.md` section silently dropped a neighbouring block. **Lesson:** diff before pushing an edit to a shared document.
- The first explanation of how the final metric numbers are computed confused the reader (answers vs claims in the denominator). **Lesson:** show the arithmetic on a real number (0.81) before describing the rule.
- Tuning the judge and validating it on the same items would have overfit. **Lesson:** keep a second, untouched test.

### How this compares with standard RAG practice
(Statements about other projects are from general knowledge, not checked against sources.)
| Common practice | Where I am |
|---|---|
| Separate retrieval and generation evaluation | Done |
| Reference-based correctness plus reference-free faithfulness and relevance | Done (own implementation) |
| Claim-level faithfulness (split into claims, verify each) | Done |
| Judge model checked against human grades; about 80% agreement is a common rule of thumb | Done, two rounds, small samples |
| A held-out set kept for milestones | Done |
| Unanswerable questions to test refusal and hallucination | Done (8 questions) |
| Oracle or ideal-context run to separate retrieval from generation faults | Done (own design, not a library feature) |
| Compare with an off-the-shelf evaluation library (Ragas, DeepEval) | **Moved to Phase 3** |
| Larger, multi-author question set; confidence intervals | Not yet; sets are small and single-author |
| Cost and latency tracking | Judge cost logged per run; no latency measurement yet (Phase 6) |

### Implications for Phase 3
Order of work, with the evidence for each. One change at a time, scored on the working set each time with the frozen judge; held-out only at milestones.
1. **Retrieval first** (the biggest gap). Candidates, matched to the failures above: chunking that keeps parentage statements and their context together (structure-aware, sentence-level or parent-child); hybrid keyword plus meaning search for names; query expansion for aliases; reranking; diversity ranking against near-duplicates and summary-passage magnets.
2. **Generation behaviour second:** the false-refusal rate (prompt and "I don't know" handling), judged on the working set only.
3. **Ragas alongside,** run on the same answers as our own metrics, to compare definitions and results; this is the step moved out of Phase 2.
4. **Open questions to investigate, not assume:** the ideal-context faithfulness dip on the working set; whether citation strictness on minor descriptors (R36, R11) distorts the citation number.
5. **Rules that stay:** do not change the judge without a new calibration (the runner warns if the fingerprint differs); never tune against held-out failures; report retrieval numbers with and without the summary passages.

### Carried over
Ragas comparison; the owner's list of retrieval observations (above); R05 correctness and R12 faithfulness remain judge disagreements; Item 1 citations in round 2 were left as "?" and excluded; the page web address in citations is still pending; prices quoted from third-party sources are unverified; the session-start hook for Graphify and claude-mem has not yet been seen running on a fresh cloud session.

---

## Phase 3 — Deep dive, one stage at a time

### What Phase 3 is (and is not)
**Goal:** take the Phase 1 baseline apart one stage at a time. For each stage: **teach the concept → build 2 or 3 methods → change ONE thing and score the working set → compare with the previous result → keep the winner and log it** (`EXPERIMENTS.md` for numbers, this file for the lesson). The point is that I can explain every stage, and why we chose what we chose, with numbers.

**Not in Phase 3:** the *types* of RAG (corrective, Self-RAG, agentic, GraphRAG) belong to Phase 5. A framework rebuild (LlamaIndex or LangChain) is Phase 4.

**Stages and the baseline problem each one targets:**
| Stage | Methods to compare | Baseline problem it targets |
|---|---|---|
| Ingestion | done in Phase 1 | |
| Chunking | fixed, recursive, sentence, semantic, structure-aware, parent-child (and sentence window) | chunk edges cutting the key sentence (R01, R20, R26, R34); right section, wrong paragraph |
| Embeddings | several models; dense vs BM25 keyword | names and spellings (Hidimba/Hidimva, Vyasa/Dwaipayana) |
| Indexing | numpy brute force, FAISS (Flat, IVF, HNSW), a vector database | no quality gain at 1,670 chunks; learn speed and memory trade-offs for when the corpus grows |
| Retrieval | top-k, MMR, metadata filters, hybrid with RRF | near-duplicates and summary passages (Sections 1, 2, 95) filling the top 5 |
| Query transformation | rewriting, multi-query, HyDE, decomposition | aliases (Partha = Arjuna); multi-hop questions |
| Reranking | cross-encoder, LLM reranker | right section, wrong paragraph (retrieve about 30, keep the best 5) |
| Generation | prompt assembly, context order, citations, "I don't know" | false refusals; citation support |

**Order:** open. Roadmap order and biggest-failure-first both start at chunking, because ingestion is done. Ragas runs alongside after the first couple of changes (moved from Phase 2).

**Rules that stay:** one variable at a time; held-out only at milestones with `--confirm-milestone`; never tune on held-out failures; frozen judge (fingerprint `2578221ecdd4`); report retrieval with and without the summary passages; do not edit the question set.

**Starting point (2026-11-05):** the data was rebuilt from the committed seed `data_seed/paragraphs.jsonl` because sacred-texts.com returned 403. Baseline reproduced exactly: hit@5 strict phrase 0.67 (16 of 24), MRR@5 0.35, section-level hit@5 0.92.

---

### Stage: Chunking — the strategies (learning first, choosing later)
Status: **learning each strategy in detail and logging it here before we choose which to build.** Done so far: recursive (detailed, library-checked), sentence-based (concept detailed) and semantic (concept detailed, measured on two passages), structure-aware (concept detailed, paragraph statistics measured), parent-child (concept detailed, previewed on R05 and R15), sentence window (concept detailed, previewed on R05 and R15), plus a section on sentence splitting (pySBD, NLTK, spaCy; pySBD and spaCy rule-based tested, NLTK not). All seven strategies are now taught in detail (2026-11-11). Nothing is built or scored yet.

#### Concept
The embedding model turns each chunk into one vector, search compares the question with those vectors, and the LLM reads the chunks it is given. So the chunk is both the unit that gets found and the unit that gets read. **Too small:** a chunk lacks context ("He then married her" with no names). **Too big:** a chunk mixes topics, its vector becomes a blurry average, and it uses up the model's reading space.

#### What our data looks like (why this matters here)
- 1,306 paragraphs; median 653 characters, longest 10,838; about 35% are over 1,000 and about 31% under 400.
- Each paragraph is one block of text with **no line breaks inside it**. Paragraphs are separated by blank lines when joined. So in practice only two kinds of boundary exist for us: paragraph and (inside a paragraph) sentence or word.
- 297 of the 1,670 baseline chunks span two sections.
- A real cut in the baseline: chunk 478 (Section 63) ends "…And from Drupada wa", and chunk 479 starts with the same 200 characters (the overlap) and continues "…Drupada was born a daughter Sikhandin…". The overlap rescued this cut, but it also makes near-twin chunks, one reason duplicates fill the top 5.

#### Strategy 1 — Fixed-size (our baseline)
- **How it works:** join all paragraphs into one long string, cut a 1,000-character window, step forward by 800 (overlap 200), repeat.
- **Built with:** plain string slicing, no library (`src/rag/chunking.py`).
- **Disadvantages:** cuts mid-word; mixes sections; loses the speaker in the middle of a long speech; overlap creates duplicates.
- **Role:** the control. Every other strategy is judged against it.

**Pending to experiment (fixed-size):**
- Keep as the control; never change its settings (1000/200) in the comparison.
- Optional size sweep (600, 800, 1000, 1500), one value at a time, as proposed in public post 2. Status: not run.

#### Strategy 2 — Recursive (learned in detail)
*Written from my own study notes (example setting: `chunk_size = 500`, `chunk_overlap = 50`), with two points checked by running the library, marked below.*

Recursive Character Text Splitting breaks a document using progressively finer separators, then merges the resulting pieces into chunks that fit within the configured size.

**1. Recursive splitting: find logical boundaries.** Default LangChain separator hierarchy: paragraph break, then line break, then space, then single character. The splitter processes the document in its original order:
1. **Paragraph:** first, split the entire document at paragraph boundaries.
2. **Line:** if an individual paragraph exceeds the size, recursively split that paragraph into lines.
3. **Space:** if an individual line still exceeds the size, split it into word-level pieces.
4. **Character:** final fallback if an individual piece is still oversized.

It does **not** automatically split every paragraph into lines or every line into words. It only moves to a finer separator for pieces that exceed the chunk-size limit.

**2. Merging: build chunks sequentially.** After recursive splitting, the resulting pieces are merged from the beginning of the document:
- Add the next piece if the combined size stays within the limit.
- If adding the next piece exceeds the limit, emit the current chunk.
- Retain approximately the overlap amount using trailing pieces from the previous chunk.
- Continue merging the remaining pieces.

A chunk can contain multiple paragraphs, or part of one paragraph followed by another. Reaching a paragraph boundary does not automatically finalize a chunk.

**3. Worked example.** A paragraph contains Line 1 (338 characters) and Line 2 (262 characters), total 600, with a 500-character limit:
- Line 1 + Line 2 = 600, which exceeds the limit.
- Chunk 1 is emitted with Line 1 (338 characters).
- Line 2 remains available for the next chunk.
- Overlap from the previous chunk is retained when constructing the next chunk.
- If Line 2 itself exceeded 500 characters, it would recursively split at spaces.

**Mental model:** recursive splitting determines **where** to break; merging determines **how much** text goes into each chunk; overlap preserves context across chunk boundaries.

**Implementation nuances:**
- `chunk_size` is a maximum target, not a requirement to fill exactly the limit.
- Words are not normally broken to fill the remaining space; character-level splitting is the final fallback.
- Overlap is approximate because the merge process retains whole pieces rather than extracting an exact substring.
- Actual output depends on separator retention and the length function (characters by default).

**Two points checked by running the library (`langchain-text-splitters` 1.1.3, 2026-11-05):**
1. **The leftover of a big paragraph does NOT merge with the next paragraph.** Test: a paragraph of Line 1 (338) and Line 2 (262), then a next paragraph of 101 characters, limit 500. Output: three chunks of 338, 262 and 101. Line 2 and the next paragraph would have fit together (363), but were not joined. A splitter we write ourselves could join them; that would be a design choice, and a separate experiment. My study notes had said the next paragraph "can be merged"; the test shows it is not, in this library.
2. **Overlap did nothing in that test** (same three chunks with overlap 0 and 50). Overlap keeps whole pieces from the previous chunk, and a 338-character piece is larger than a 50-character overlap, so nothing was kept. It matters only when the pieces being merged are small.

**On our data:**
- **The default ladder has no sentence level**, and our paragraphs contain no line breaks. So an oversized paragraph drops straight to splitting at **spaces**, which cuts mid-sentence. Test on our longest paragraph (Section 1, 10,838 characters, limit 1,000, no overlap): **11 chunks, 9 of which end without closing punctuation**, for example ending "…When I", "…race of Madhu," and "…imprisoning Krishna". **I had told the owner earlier that sentence ends were part of the ladder; that was wrong for the default.** To cut at sentence ends we must add a sentence separator ourselves. With a full stop added to the ladder the same paragraph gave 13 chunks; the library appeared to move the full stop to the start of the next chunk (to confirm when we build).
- Only the first chunk of that speech names the speaker. Recursive chunking does not fix that.
- Because the baseline joined everything into one string, "run it per section" versus "run it over the whole text" is a choice that decides whether chunks cross section boundaries.

**Disadvantages (summary):** still size-driven; with the default separators it cuts mid-sentence in long paragraphs; the speaker is lost in long speeches; whether related sentences end up together is luck.
**Built with (if we build it):** our own short loop (an ordered separator list, split, merge) so that I can explain it, using the library only as a reference to compare against.
**Chunks versus failures:** key line cut at a boundary: improved only if a sentence separator is added; sections crossing: depends on running per section; speaker lost: not fixed.

**Pending to experiment (recursive):** each is its own one-variable experiment; none run yet.
1. Add a sentence-level separator to the ladder (paragraph, then sentence, then space), against the default ladder.
2. Run per section versus over the whole text (whether chunks may cross sections).
3. Leftover of a big paragraph: stays its own chunk (library behaviour) versus joins the next paragraph (our own version).
4. Overlap: none versus a small overlap (and note it only matters when pieces are small).
5. Chunk size (for example 500, 1000), after the ladder question is settled.

#### Strategy 3 — Sentence-based / sentence-aware (concept learned; splitters not yet tested)
*Written from my own study notes (example setting: `chunk_size = 1000`, `chunk_overlap = 200`), with additions from our data marked "Our data" and two checks marked "Checked".*

Sentence-aware chunking identifies complete sentences first, then combines consecutive sentences into chunks that fit within the configured size. Unlike Recursive Character Splitting, it uses linguistic sentence boundaries rather than progressively trying paragraph, line and word separators.

**Step 1 — Split the entire document into sentences.** The sentence tokenizer processes the input text and returns an ordered list of sentences (Sentence 1, Sentence 2, Sentence 3, and so on). Available options:

| Approach | How it works | Considerations |
|---|---|---|
| Regex-based | Splits on punctuation such as `.`, `?`, `!` | Simple, but can mistake abbreviations and decimals for sentence boundaries |
| NLTK | Uses Punkt sentence tokenization | Handles many common abbreviations and sentence patterns |
| spaCy | Uses a language pipeline to identify sentence boundaries | Can use parser-based or rule-based sentence segmentation |
| Language-specific tokenizers | Uses segmentation designed for a particular language | Useful for languages with different sentence-boundary conventions |
| Custom rules | Combines punctuation, abbreviations and domain-specific rules | Requires maintenance and testing |

Common implementations: NLTK `sent_tokenize()` and spaCy's sentence segmentation. (Also on my list for our test: pySBD, a rule-based splitter.)

**Step 2 — Handle oversized sentences.** Each sentence is checked against the 1,000-character limit: 300 characters is retained as one sentence; 800 characters is retained as one sentence; 1,200 characters exceeds the limit. Available options:

| Strategy | How it works | Trade-off |
|---|---|---|
| Keep sentence intact | Allow a chunk to exceed the limit | Preserves sentence integrity, but violates the size target |
| Word-level fallback | Split the sentence at word boundaries | Avoids breaking words, but may split one thought |
| Recursive fallback | Try spaces, punctuation and progressively smaller separators | More flexible, but can fragment a sentence |
| Token-level fallback | Split based on model-token boundaries | Controls token count, but may break linguistic units |
| Custom semantic fallback | Find a sensible internal boundary using linguistic or semantic rules | More complex to implement |

**Important (from my notes):** standard LangChain `NLTKTextSplitter` and `SpacyTextSplitter` do not automatically apply recursive splitting to an oversized sentence. Their merge logic can produce an oversized chunk. A hybrid implementation is needed if recursive fallback is desired.
- **Checked (2026-11-11, `langchain-text-splitters` 1.1.3, spaCy 3.8.18, rule-based `sentencizer`):** a 1,231-character sentence with a 500-character limit came out as one 1,231-character chunk, with a warning "Created a chunk of size 1231, which is longer than the specified 500". Confirmed for the spaCy splitter. **Not checked for the NLTK splitter:** its sentence data (`punkt_tab`) could not be downloaded in the cloud environment (host not allowed), so the NLTK claim rests on my notes until we can test it.

**Step 3 — Merge consecutive sentences.** Start at the beginning of the sentence list and accumulate sentences: add the next sentence if the combined size remains within 1,000; if it exceeds 1,000, emit the current chunk; continue with the remaining sentences. Example: S1 = 300, S2 = 250, S3 = 350, S4 = 400, S5 = 200 characters. S1 + S2 + S3 = 900. Adding S4 gives 1,300, so Chunk 1 is emitted at 900 characters.

**Step 4 — Apply overlap.** The next chunk retains context from the previous chunk. Two approaches:
- **Sentence-based overlap:** retain complete trailing sentences. Actual overlap may be less or more than the target, depending on the implementation.
- **Character-based overlap:** retain the last 200 characters, potentially cutting through a sentence.

Overlap is a separate decision from sentence detection.

**Mental model:** the sentence tokenizer determines **where** sentences end; the merger determines **how many** sentences fit into each chunk; overlap preserves context between adjacent chunks.

**Limits:** sentence-aware chunking preserves grammatical boundaries, but a complete sentence is not necessarily a complete thought. Relationships between consecutive sentences may still require additional context.

**For the Mahabharata corpus:** preserve Parva, section and paragraph metadata alongside the resulting chunks. This allows sentence-level segmentation without losing the source hierarchy or provenance.

**Our data (what the splitters will have to cope with)** — rough counts from a quick pattern search of the 1.3-million-character corpus, covering only the patterns I searched for:
- Full stop followed by a closing quote (`."` or `.'`): about 1,559. The quote belongs to the sentence that just ended.
- Abbreviation-like cases ("Mr.", "Dr.", "viz."): about 71. Real examples: "Mr. Pickford", "Dr. Rost's letter", "viz. he would grant…".
- Semicolons: about 727. Splitters do not split at them, so lists such as chunk 478's "from Arjuna, Srutakirti; from Nakula, Satanika; …" stay one very long sentence (longer than 1,000 characters), so the oversized-sentence rule (Step 2) will matter.
- Source typos that look like sentence ends: "When I heard that Nakula. the son of Madri…" has a full stop where a comma belongs, and "my union with the? took place" has a stray question mark. A splitter will cut there; no splitter can fix a typo in the source.
- Paragraph and speaker are still not handled by this strategy: a chunk can hold the end of one speech and the start of another unless sentences are packed within a paragraph only, and a chunk from the middle of a long speech does not say who is speaking.

**Design questions to decide when we build it:** pack within a paragraph only, or across paragraphs; what to do with sentences longer than the limit (keep intact, or fall back); sentence overlap or character overlap or none. Each is its own one-variable experiment.

**Still to do for this strategy:** test pySBD, NLTK Punkt and spaCy (rule-based and parser-based) on our paragraphs, compare their sentence counts, and hand-check the hard cases above. NLTK needs its sentence data, which the cloud environment currently blocks; options are to allow the download host, or to commit the small data file. Then build and measure.

**Pending to experiment (sentence-based):** none run yet.
1. Splitter comparison first (see "Sentence splitting" below): pySBD with the quote fix, spaCy rule-based with an abbreviation fix, NLTK Punkt once its data is available (allow the download host, or commit the small data file), spaCy parser mode if its model can be downloaded.
2. Pack within a paragraph only, or across paragraphs within a section.
3. Sentences longer than the limit: keep intact, or fall back to a finer split.
4. Overlap: none, sentence overlap, or character overlap.
5. Chunk size.

#### Strategy 4 — Semantic (concept learned; not built or scored)
*Written 2026-11-11. "Checked" marks something I ran or read in the source this session; "general knowledge" marks what I know but did not verify here.*

**The problem it solves.** Fixed-size, recursive and sentence-based chunking cut by size or punctuation; none looks at meaning. Semantic chunking asks: **where does the topic actually change?** It cuts there, so each chunk is about one thing.

**The method, step by step**
1. **Split into sentences**, per paragraph (never on joined text). This step is crucial and has its own section below ("Sentence splitting").
2. **Embed every sentence** with the embedding model, so each sentence becomes a vector (here `BAAI/bge-small-en-v1.5`, vectors of length 384, normalised to length 1).
3. **Measure how similar each sentence is to the next** (cosine similarity; for normalised vectors this is just the dot product). High means "still on the same topic"; low means "something changed". For n sentences there are n − 1 similarity values; value i sits between sentence i and sentence i + 1.
4. **Choose the cut points with a breakpoint rule:**
   - **Percentile:** cut where the similarity is in the lowest N% of all values (for example the lowest 10%). The number of cuts is predictable, but a fixed share of boundaries is cut by construction, whether or not a real topic change exists.
   - **Standard deviation:** cut where a value is more than N standard deviations below the average. It adapts to each passage: if all similarities are close together, few or no cuts happen.
   - **Fixed threshold:** cut wherever similarity is below a set number (for example 0.6). Simple, but the right number belongs to the embedding model and must be re-tuned if the model changes.
   - Other rules exist (general knowledge: for example interquartile range and gradient-based rules in LangChain's experimental semantic splitter); not studied.
5. **Apply size limits and group.** Without limits, the rule can produce one-sentence chunks and giant chunks. A minimum and a maximum size are usual. Sentences between two cuts become one chunk, carrying section and paragraph metadata.

**How chunks actually form (the owner's question, 2026-11-12): no chunk size is needed.** The cut points come from the similarity values and the breakpoint rule, not from a size. Size appears only as optional guards (a minimum and a maximum) applied afterwards. Worked example, checked on the whole Section 66 genealogy paragraph (23 sentences, sentence lengths 33 to 252 characters, about 1,980 characters in all; pySBD for the sentences, `bge-small-en-v1.5` for the vectors):
1. **22 similarity values** sit between the 23 sentences (0.81, 0.76, 0.61, 0.56, 0.50, 0.72, 0.58, 0.56, 0.69, 0.61, 0.60, 0.55, 0.68, 0.52, 0.77, 0.71, 0.52, 0.57, 0.67, 0.61, 0.58, 0.64).
2. **Breakpoint rule = percentile.** The 10th percentile of the 22 values is 0.523; every gap below it is a cut. Chunks: S1-S5 (281 characters), S6-S14 (789), S15-S17 (261), S18-S23 (649). A chunk is simply the run of sentences between two cuts.
3. **A looser rule (25th percentile, threshold 0.563)** cuts more: S1-S4 (245), **S5 alone (36 characters)**, S6-S8 (386), S9-S12 (242), S13-S14 (161), S15-S17 (261), S18-S23 (649). One chunk is a single 36-character sentence: this is why a **minimum size** guard is needed.
4. **Minimum size guard (300 characters) on that result:** a chunk smaller than the minimum is merged into the next chunk. Result: S1-S8 (667), S9-S14 (403), S15-S23 (910).
5. **Maximum size guard (500 characters) on the 10th-percentile result:** a chunk over the maximum is split again at its own lowest-similarity gap, repeating until every piece fits. S6-S14 (789) became S6-S8 (386) and S9-S12 (242) and S13-S14 (161); S18-S23 (649) became S18 (188) and S19-S23 (461). The chunk list: S1-S5, S6-S8, S9-S12, S13-S14, S15-S17, S18, S19-S23.
So the order is: **embed, compare neighbours, cut by the rule, then enforce minimum and maximum.** The minimum and maximum are design choices (which merge direction, which split point) and are variables of their own. The numbers are one paragraph and one embedding model, so they show the mechanism, not how the rules behave on the corpus.

**Variations (general knowledge, not built):** compare a small window of sentences with the next window instead of single sentences (smooths noisy short sentences); compare each new sentence with the whole chunk built so far instead of only its neighbour; let an LLM decide where to cut (expensive; out of scope).

**Embedding is used twice:** once to choose the chunks, and again to index the chunks for search. The two models need not be the same. Using the same one keeps things simple.

**Worked example on our text — Section 66 (file `section_067.html`), the genealogy paragraph of Brahman, Manu and the Vasus.** Checked: pySBD split the paragraph into **23 sentences**; the table below covers only the **first 12** (my display limit when I first measured it; I wrongly described the paragraph as having 12 sentences until 2026-11-12). `bge-small-en-v1.5` embedded each sentence, and neighbour similarity (value after sentence i) for the first 12 came out as:

| After sentence | Opening words | Similarity to the next |
|---|---|---|
| 1 | "And Brahman had another son named Manu." | 0.81 |
| 2 | "And Manu had a son of the name of Prajapati." | 0.76 |
| 3 | "And the sons of Prajapati were eight…" | 0.61 |
| 4 | "They were Dhara, Dhruva, Soma, Aha…" | 0.56 |
| 5 | "These eight are known as the Vasus." | **0.50** (lowest) |
| 6 | "Of these, Dhara and the truth-knowing Dhruva were born of Dhumra…" | 0.72 |
| 7 to 11 | one-line "And X had a son Y" sentences | 0.56 to 0.69 |

Over these first 12 sentences (11 values): range 0.50 to 0.81, mean 0.64. Over all 23 sentences (22 values): range 0.50 to 0.81, mean 0.63; the values after sentences 12 to 22 are 0.55, 0.68, 0.52, 0.77, 0.71, 0.52, 0.57, 0.67, 0.61, 0.58, 0.64. Reading it:
- The lowest dip (0.50) is between "These eight are known as the Vasus." and "Of these, Dhara and Dhruva were born…". Sensible as a topic shift (introducing the eight versus their children), but a question such as "Who were the sons of the Vasus?" needs both halves, so the cut separates two parts of one answer.
- The whole range is narrow and values from 0.56 to 0.69 are everywhere. In a genealogy all sentences look alike, so cuts are mostly noise; a percentile rule cuts a fixed share regardless.

**Disadvantages on our data**
- **Genealogies:** few real topic shifts, so the cuts are noise, or (with a strict rule) the chunks become very long.
- **Dialogue:** "X said…" turns alternate, so neighbours can look dissimilar inside one conversation.
- **Short sentences** ("These eight are known as the Vasus.") give noisy vectors, so comparisons are unreliable.
- **Sentence splitting errors come in** (see below): a wrong split makes the comparison between wrong pieces.
- **Cost:** every sentence in the corpus is embedded once to choose chunks and again to index them. Not prohibitive (the full corpus embedded in about 90 seconds as chunks), but it is an extra pass and the rule needs tuning.
- **Expectation (general knowledge, not checked):** published comparisons are mixed, and semantic chunking often does not beat simpler methods by much. Our data (lists, dialogue, short sentences) is where it should struggle, so the value for us is learning how it behaves and letting our own measurement decide.

**Design choices that become experiment variables (one at a time)**
1. Sentence splitter, and any cleaning before it (see the section below).
2. Whether a chunk may span paragraphs, or stays inside one paragraph. Inside one paragraph: never mixes two speeches, but a short paragraph (median paragraph 653 characters; about 31% under 400) becomes its own chunk. Across paragraphs within a section: a question and its answer (Section 5, first two paragraphs) could join, but a chunk can mix speakers. Never across sections.
3. The breakpoint rule and its value (percentile, standard deviation, fixed threshold).
4. Minimum and maximum chunk size.
5. Single sentences or a window of sentences for the comparison.
**How we would score it:** retrieval metrics first (hit@5, MRR@5, with and without the summary passages; free and fast, after a re-embed of about 90 seconds); the frozen judge only for a setting that looks like a winner (it costs money and shows run-to-run noise, for example faithfulness flipping 1.0, 0.75, 1.0 on one answer earlier). The winner is compared with the baseline and with the other strategies we choose.
**Status:** concept only. The four choices above are not made; the owner wanted to learn each option first.

**Pending to experiment (semantic):** none run yet. The owner chose to learn each option before deciding.
1. Choose the splitter (depends on the splitter comparison below); hold it fixed.
2. Decide: chunks stay inside one paragraph, or may span paragraphs within a section.
3. Vary the breakpoint rule one at a time: percentile (start near the lowest 10%), standard deviation, fixed threshold; then its value.
4. Minimum and maximum chunk size.
5. Single sentences versus a window of sentences for the comparison.
6. Score with retrieval metrics first; the frozen judge only for a likely winner.

#### Sentence splitting: the crucial first step (for sentence-based and semantic chunking)
Both strategies depend on knowing where sentences end, so every splitting mistake flows into the chunks. Our text is hard for splitters: about 1,559 full stops followed by a closing quote, about 71 abbreviation-like cases ("Mr.", "Dr.", "viz."), about 727 semicolons (lists stay one long sentence), and typos in the source ("When I heard that Nakula. the son of Madri…", "my union with the? took place"). These counts are rough, from a quick pattern search of the corpus, and cover only the patterns I searched for.

**Rule 1 — split each paragraph separately, never joined text.** Checked: on the first six paragraphs of Section 5 pySBD returned 1, 3, 9, 3, 8 and 3 sentences when run on each paragraph; on the same text joined together it returned a 2,639-character "sentence" plus two more, because quotes opened in one paragraph paired with quotes much later.

**The three families of splitter**
- **pySBD (rule-based; version 0.3.4).** Checked in the source (`between_punctuation.py`, `punctuation_replacer.py`): it finds text enclosed in a matching pair of quotes (`"…"`, `'…'`, curly quotes, brackets, parentheses, dashes) and replaces every `.`, `?` and `!` inside with a placeholder, so the boundary step cannot see them; the placeholders are restored afterwards. A quoted span is therefore one unbreakable unit.
- **NLTK Punkt (statistical; version 3.10.4 installed).** General knowledge, **not run here**: unsupervised. It learns from text which words are abbreviations (short words, often with internal full stops, often written with a full stop attached), plus common word pairs ("Mr. Smith") and common sentence starters, and looks at whether the next word is capitalised. It ships a trained English model and can be retrained on our own text without labels (an idea to test: it might learn "viz." and "i. e." from our corpus). It depends on the full stop; as far as I know it has no special quote handling. It might avoid cutting at "Nakula. the son" because the next word is lowercase (to be tested). **Its data file (`punkt_tab`) could not be downloaded in the cloud environment** (host not allowed; NLTK's proxy safeguard refuses, and I did not override it).
- **spaCy (version 3.8.18).** Two modes. The **rule-based `sentencizer`** (checked, works offline): ends a sentence after a `.`, `?` or `!` token and keeps a following closing quote with that sentence; no abbreviation list of its own (the tokenizer treats many common abbreviations as single tokens; general knowledge). The **parser mode** (general knowledge, not tested): a trained neural model that reads the grammar and predicts where sentences begin; copes with missing punctuation, but needs a downloaded language model (probably blocked here), is slower, and was trained on modern English, so "thou hast" and "hath" may confuse it. A light statistical `senter` component also exists in the trained models (same download).
- **Regex and custom rules** (general knowledge): split on `. ? !` followed by a capital; simple but fooled by abbreviations; custom rules need upkeep and testing.

**What went wrong on our text (checked)**
1. **pySBD returns one sentence for whole-paragraph speeches.** Example: Section 5, paragraph index 0 (heading "SECTION V", file `section_006.html`), Saunaka's question: 487 characters, five sentences, opens with `"` and closes with `."`, so pySBD sees a quote pair and hides the full stops. Result: 1 sentence of 487. Rough scan: **178 of 1,306 paragraphs** (about 14%) where pySBD returns one sentence although the paragraph has two or more apparent sentence ends (criterion: more than 300 characters and at least two apparent ends); **177 of those 178 start with an opening quote**. Paragraphs in the middle of a long speech open with `"` but do not close it (the speech continues), so there is no pair and they split normally.
   - Test on the real paragraph: as is gives 1 sentence (487); removing both outer double quotes gives 5 sentences (136, 35, 168, 79, 63); removing only the opening or only the closing quote also gives 5. Toy checks agree: `"One. Two. Three."` stays one sentence; `"One. Two. Three.` (never closed) splits into three.
   - **Possible fix, untested at scale:** strip the outer double quotes before splitting, and restore them (or record that the paragraph was quoted) when building the chunk. To do: re-run the scan and see how many of the 178 this fixes and whether it breaks anything.
2. **spaCy's rule-based splitter did not have the quote problem:** none of the same 178 paragraphs came back as one sentence.
3. **Each splitter fails somewhere else (spot check on six short strings modelled on corpus sentences; a spot check, not a benchmark):**

| Case | pySBD | spaCy rule-based |
|---|---|---|
| "Mr. C.H. Tawney says…" | correct | correct |
| "…habit, viz. he would grant…" | correct (kept whole) | **cut after "viz."** |
| "…i. e. , without providing…" | **cut into 3 pieces** | correct (kept whole) |
| "Nakula. the son of Madri" (source typo) | cut | cut |
| closing quotes `."` and `.'` | correct | correct |
| semicolon-joined list | one long sentence | one long sentence |

4. **Neither can fix a typo in the source:** a full stop where a comma belongs is cut by both.

**Conclusion so far.** No splitter is free of errors on our text; each has different weak spots. pySBD needs a quote-stripping step; spaCy's rule-based version needs an abbreviation fix ("viz."). NLTK and spaCy's parser mode are not tested. **Earlier I listed "pySBD only" as the recommended choice for the first semantic experiment; I withdrew that after finding the quote problem.** The next step is a splitter comparison: hand-check a sample of paragraphs, count each splitter's errors, then choose a base splitter and add small fixes for its known gaps.
**Gotchas:** (a) test the splitter on joined text and on single paragraphs; they differ hugely; (b) a count of "sentences" does not show correctness, only reading the output does; (c) the rule-based splitters hide full stops inside quotes by design.

**Pending to experiment (sentence splitting):** none run yet.
1. Re-run the corpus scan after stripping outer double quotes, to see how many of the 178 quote-wrapped paragraphs are fixed and whether anything else breaks.
2. Splitter comparison: hand-check a sample of paragraphs and count each splitter's errors (pySBD with the quote fix, spaCy rule-based, NLTK Punkt, spaCy parser mode).
3. Fix known gaps: an abbreviation list for spaCy ("viz."), the "i. e. ," case for pySBD.
4. NLTK data: allow the download host in the environment settings, or commit the small data file.
5. Idea to test: retrain Punkt on our own text (no labels needed).

#### Strategy 5 — Structure-aware / paragraph-based (concept learned; not built or scored)
*Written 2026-11-11. "Measured" means computed from `data/processed/paragraphs.jsonl` this session.*

**The problem it solves.** Fixed-size cuts by character count, and sentence-based and semantic chunking guess where thoughts end. Structure-aware chunking uses the boundaries the text already marks: **paragraphs, sections and the "X said…" speaker tags**. The translator already decided where one thought ends, so a chunk should follow that instead of a count.

**What structure our data carries.** Each cleaned paragraph already has: source file, heading (for example "SECTION V"), sub-parva, paragraph index, printed page, how many page-break fragments were merged, and the section number (`None` for the translator's preface). So the section, position and page of every chunk are known, which citations need.

**The method, step by step**
1. **One paragraph, one chunk** when the paragraph is a sensible size.
2. **Merge tiny paragraphs** with a neighbour, only within the same section.
3. **Split very long paragraphs** into pieces at sentence boundaries (this needs a sentence splitter; see "Sentence splitting").
4. **Repeat the speaker as a header** on the pieces ("Sauti said: …"), so each piece still says who is talking.
5. **Never cross a section boundary;** attach section, paragraph and page metadata to every chunk.

**Measured on our corpus (1,306 paragraphs, median 653 characters, mean 1,021)**

| Paragraph length (characters) | Share |
|---|---|
| under 100 | 3.2% |
| 100 to 200 | 10.8% |
| 200 to 400 | 17.0% |
| 400 to 1,000 | 34.4% |
| 1,000 to 2,000 | 21.5% |
| 2,000 to 5,000 | 11.7% |
| over 5,000 | 1.4% |

- **Most of the text sits in long paragraphs.** 452 paragraphs (35%) are over 1,000 characters and hold about **71% of all the text** (951,271 of 1,333,251 characters). So step 3 applies to most of the corpus: for us, structure-aware chunking is largely "split long paragraphs well", so it depends on the sentence splitter and inherits its quote and abbreviation problems.
- **Speaker tags are common.** About 52% of paragraphs (685) start with "X said / answered / replied…" (rough pattern match that only catches a few verbs, so an undercount). Of the 452 long paragraphs, 250 start with a speaker tag. If such a paragraph is split, only the first piece names the speaker; that is the case for a header.
- **Sections are small.** 237 sections, median 4 paragraphs (smallest 1, largest 48). Never crossing a section means a short section gives few chunks. (In the baseline, 297 of 1,670 chunks crossed a section boundary.)

**Examples from our text**
- **Tiny paragraphs:** "Kisari Mohan Ganguli" (20 characters) and "Calcutta" (8) are front matter from the translator's preface (no section number); "So ends the sixth section called "the curse on Agni" in the Adi Parva." (70 characters). Whether these get a chunk, get merged, or are dropped is a rule to choose.
- **Merging is not always possible.** Section 1's first paragraphs are 138, 990, 180, 1,156, 800, 1,206, 1,341 and 483 characters. With a 1,000-character cap the 138 cannot join the 990 (1,128 together), and the 180 cannot join the 1,156. They would stay as small chunks, unless the cap is loosened or the small paragraph is attached to the next chunk. A design decision with no obvious answer.
- **The speaker header.** Section 2, paragraph 4 (1,609 characters) begins "Sauti said, 'One chariot, one elephant, five foot-soldiers, and three horses form one Patti…". Split into two, the second piece would no longer say Sauti is speaking. With a header, both read "Sauti said: …". Whether the header is part of the embedded text, or only stored as metadata for display, is a variable to test: in the text it may help questions like "What did Sauti explain?" and may also add noise.

**Disadvantages (understood by the owner)**
- Very uneven chunk sizes: a few characters up to over 10,000 before splitting. Small chunks give weak vectors; big ones are the problem we wanted to avoid.
- It depends on the quality of ingestion (our paragraph boundaries came from Phase 1 cleaning, including gluing sentences split by page breaks).
- A speech running across many paragraphs carries the speaker tag only on the first; later paragraphs open with a quotation mark but no speaker. Carrying the last speaker forward is possible but risky and untested.
- The thresholds (what counts as tiny, what counts as too long) are our own choices, each a variable.
- It relies on a sentence splitter for long paragraphs, so the splitter findings apply here too.

**Key problem: large paragraphs, and why a good sentence splitter is essential here (measured 2026-11-11).**
- **The scale.** 452 of 1,306 paragraphs are over 1,000 characters and hold 951,271 of 1,333,251 characters (**71.3%** of the corpus). 18 paragraphs are over 5,000 characters (122,789 characters in total); the longest is 10,838. 435 of the 452 long paragraphs start with a quotation mark (speeches).
- **Why this decides the strategy.** "Keep the paragraph whole" works only for the minority of text that sits in short paragraphs. For 71% of the text the strategy must split inside paragraphs, and the only structure left inside a paragraph is sentences. So structure-aware chunking is, in practice, paragraph structure for the short ones plus sentence splitting for the long ones. If the splitter is wrong, the strategy is wrong for most of the corpus.
- **What a bad splitter does to it (the same long paragraphs, two splitters):**

| | pySBD (default use) | spaCy rule-based |
|---|---|---|
| Long paragraphs returned as ONE sentence | **94** (214,681 characters = 22.6% of the long-paragraph text, about 16% of the whole corpus) | 0 |
| Sentences over 1,000 characters inside long paragraphs | **157** | 8 |
| Total sentences found in the long paragraphs | 4,735 | 8,006 |

  A paragraph that comes back as one "sentence" cannot be split at a sentence end, so the chunker would have to cut it at a size limit again (the baseline's problem), or keep a huge chunk. That is the quote-pair behaviour described in "Sentence splitting" (a paragraph that opens and closes with a double quote is treated as one unbreakable unit). spaCy's rule-based splitter did not have that problem but has its own errors (it cut after "viz."; see the spot check).
- **What is still unknown.** The counts show how many long paragraphs a splitter fails to split, not how many it splits in the wrong place; that needs the hand-check sample in the splitter comparison. The 8 spaCy sentences over 1,000 characters are probably semicolon lists like chunk 478's (not checked). The numbers come from the default pySBD call and spaCy's `sentencizer`, with no cleaning (the quote-stripping fix was not applied here).
- **Consequence for the plan.** The splitter comparison is not optional for this strategy: it comes before any structure-aware experiment, and the maximum chunk size and the oversized-sentence rule (keep intact or fall back) should be decided with the long-sentence counts above in view.

**How it would be built.** Our own loop over `paragraphs.jsonl`: group by section; apply the merge and split rules; add the header to split pieces; write each chunk in the same format as the baseline (text, section numbers, positions) so the existing embedding, search and evaluation code works unchanged. Not yet checked: that the retrieval evaluation does not depend on chunk IDs (it scores the evidence phrase and the gold section); confirm before the first run. Crude size estimate, ignoring sentence boundaries: roughly 1,900 chunks against the baseline's 1,670. Treat as rough.

**Which failures it might fix.** Key line cut at a boundary (R01, R20, R26, R34): yes for long paragraphs, if split at sentence ends. Right section but wrong paragraph (R05, R08, R12): paragraph-sized chunks (median 653) should line up better with where answers sit. Speaker lost in long speeches: the header addresses it.

**Pending to experiment (structure-aware):** none run yet; each is one variable at a time.
1. Decide what counts as "tiny" and whether tiny paragraphs merge, stay, or (for front matter) are dropped.
2. Decide the maximum size and what to do when a small paragraph cannot merge under it (looser cap, or accept small chunks).
3. Choose the sentence splitter for long paragraphs (depends on the splitter comparison; this is a prerequisite, because 71% of the text is in long paragraphs and pySBD left 94 of them unsplit; see "Key problem" above).
4. Speaker header: none, metadata only, or part of the embedded text.
5. Carry the speaker forward across paragraphs of one speech (risky; optional).
6. Confirm that the retrieval evaluation is independent of chunk IDs before the first run.
7. Score with retrieval metrics first; the frozen judge only for a likely winner.

#### Strategy 6 — Parent-child (concept learned; previewed on two questions; not built or scored)
*Method section written from my own study notes (example setting: parent = 1,000 tokens, child = 200 tokens, "illustrative values, not fixed requirements"). The sections "What we saw" and below were written 2026-11-11; the previews are not evaluations.*

**Parent-child chunking: how it works (my notes)**
**Overview.** Parent-child chunking is a hierarchical retrieval strategy that separates **retrieval precision from context delivery**. It creates two levels of chunks:
- **Parent chunks:** larger passages that preserve broader context.
- **Child chunks:** smaller passages used for embedding and vector retrieval.

The retriever searches child chunks but fetches their corresponding parent chunks to provide context to the LLM.

**Step 1 — Create parent chunks.** Parent chunks preserve meaningful context. Parent creation has no prescribed splitting algorithm. Options: fixed-size splitting, recursive splitting, structure-aware splitting, semantic splitting. For the Mahabharata corpus, a structure-first approach is worth investigating: create parents from coherent groups of paragraphs while respecting section boundaries. A parent does not have to represent an entire section; one section can contain multiple parents.

**Step 2 — Split parents into child chunks.** Each parent is divided into smaller units, which become the primary retrieval units. Options: fixed-size, recursive, sentence-aware, semantic, structure-aware splitting. A possible hybrid: sentence-aware splitting within each parent, with recursive fallback for oversized sentences or groups. Children do not need to be independently understandable in every implementation; they can rely on their parent for additional context.

**Step 3 — Maintain parent-child relationships.** Every child must have a reference to its parent. Example fields: a parent has `parent_id` (for example "ADI_66_P001"), `text`, parva ("Adi Parva") and section (66); a child has `child_id` (for example "ADI_66_P001_C001"), `parent_id` and `text`. Important implementation choices:
- Assign unique parent and child IDs.
- Preserve source metadata.
- Store the parent text separately from the child embeddings.
- Maintain deterministic parent lookup.
- Avoid relying on text similarity to reconstruct parent-child relationships.

**Step 4 — Embed and index child chunks.** Generate embeddings for the child chunks and store them in the vector database. Typical flow: generate an embedding for each child; store the vector and child text; store the corresponding parent ID as metadata; keep parent text in a document store or another retrievable storage layer. **Do parent chunks also need embeddings?** Not in the standard child-retrieval approach. Parent embeddings are optional and only needed if you want an additional parent-level retrieval mechanism.

**Step 5 — Retrieval and parent lookup.** When a user submits a question: (1) generate the question embedding; (2) search the vector database for relevant child chunks; (3) retrieve the matching child IDs and parent IDs; (4) fetch the corresponding parent chunks; (5) deduplicate parents if multiple children point to the same parent; (6) pass the selected parent context to the LLM. Example: for "Who were Dhara's sons?", vector search identifies the child discussing Dhara's descendants, the system obtains its parent ID, the parent passage is fetched, and the LLM receives the broader genealogy context.

**Key principle:** retrieval operates on children; context delivery operates on parents.

**How it fits our project (my additions)**
- **A real instance of the Dhara example.** In our text the sentence "And Dhara had two sons, Dravina and Huta-havya-vaha." sits in Section 66 (heading SECTION LXVI, file `section_067.html`, paragraph index 1, sub-parva Sambhava Parva), a 2,002-character paragraph listing the Vasus and their sons. That paragraph would be the parent and the sentence the child. Illustration only: I did not run this search.
- **Sizes in our terms (approximate).** Our baseline chunks of 1,000 characters measured about 247 tokens at the median (roughly 4 characters per token). So a 200-token child is about 800 characters, close to a whole baseline chunk, and a 1,000-token parent is about 4,000 characters, larger than most of our paragraphs (median 653 characters). The parents are not embedded, so the embedding model's 512-token limit applies only to children.
- **It is a pattern that touches two stages, not a standalone splitter.** The chunking part defines two levels and the link between them; the retrieval part does the swap and the de-duplication after the search. It needs a method for each level: children can come from any earlier strategy (sentence-based, small recursive chunks, semantic), parents from structure-aware paragraphs or larger recursive chunks. It is a layer on top of the earlier strategies, so it multiplies the experiments (two levels to choose).
- **Index size.** With sentence-sized children the index would hold about 11,689 vectors instead of 1,670 baseline chunks (count from the spaCy rule-based splitter; median child 99 characters).

**What we saw: a preview on two working-set questions (2026-11-11; previews, not scores)**
Setup: children were all 11,689 sentences (spaCy rule-based splitter, per paragraph; median 99 characters, 837 under 40 characters); the parent was the paragraph a sentence came from; the five best children per question. Script not committed (scratchpad only). Both questions are from the working set.
- **R05, "Who set fire to the Khandava forest, and why?"** The baseline found no evidence phrase in its top 10. Here the best child was a sentence from Section 225 ("Beholding Khandava on fire…") whose parent paragraph (2,745 characters) contains an evidence phrase. So the swap rescued this question in the preview: an example of "right section, wrong paragraph" being fixed. The other four children were about Khandava but came from other passages (Sections 230, 2, 232, 231), and their parents contain no evidence phrase. All five parents were distinct. Parent sizes ranged from about 1,800 to 5,900 characters.
- **R15, "Who is Sauti's father?"** The baseline found the evidence at rank 1. Here the top five children were tiny fragments such as `"Sauti said. '` (14 characters, twice), `"Sauti continued, 'O son of Bhrigu!` (35) and `'Sauti continued, 'Then Agni replied…` (68), plus "He was the father of Vasudeva." They match through the name "Sauti" only; none of their parents contain an evidence phrase. In the preview it did worse than the baseline.
- **What the previews show:** (1) the swap can fix "right section, wrong paragraph"; (2) very short children match on a name alone, and our text has many short "X said." fragments, so the name problem (our central challenge) returns through tiny children; (3) parents are large; (4) two questions show behaviour, not performance.

**Disadvantages (what we know)**
1. **Child noise.** Small children make noisy matches, as in R15. A better sentence splitter helps, but the R15 fragments are real short sentences, not splitter errors, so the fix also needs a **minimum child size** (merge any sentence under some length with the next, so "Sauti said." travels with the speech it introduces) or sentences grouped into small pieces.
2. **Large parents and the reading budget.** A parent can be thousands of characters (one paragraph is 10,838), so five parents can use up the model's reading space. Parents need a cap (for example about 2,000 characters), with the part of the paragraph around the matching child used when a paragraph is longer.
3. **Duplicate parents.** Several children of one parent can match, so the same parent appears more than once. Rather than a fixed top 20, rank all children, walk down the list and collect parents, skipping repeats, **until there are 5 distinct parents**; the number of children looked at then adjusts itself.
4. **Balancing the sizes.** Child size, parent size, minimum child size and the parent cap are all variables; each is tested one at a time.
5. **More moving parts:** two levels, an ID lookup, a swap step, about 11,689 vectors instead of 1,670, and quality that depends on the splitter when children are sentences.
6. **The scoring trap.** We must score the **parent text**, because that is what the model sees. A larger text contains an evidence phrase more easily, so the hit rate rises almost by construction. For a fair comparison, also record how many characters each method hands to the model, and rely on end-to-end correctness for the final judgement. Not yet checked: how the evidence-phrase check treats a phrase that spans two paragraphs.

**Pending to experiment (parent-child)**
None run yet; one variable at a time; the splitter comparison and the single-level strategies come first, so parent-child builds on the best of them.
1. Fix the child method (best splitter and chunking result so far), then vary the **minimum child size** (none, then a minimum such as 100 and 200 characters).
2. Fix the children, then vary the **parent unit**: the paragraph, the paragraph capped (for example 2,000 characters), a group of paragraphs within a section.
3. **Retrieval rule:** walk down the ranked children until 5 distinct parents (versus a fixed number of children).
4. Order the parents by their best child's score; compare with keeping book order.
5. Measure the **characters passed to the model** next to hit@5 and MRR@5, and use end-to-end correctness from the frozen judge for the winner only.
6. Check how the evidence-phrase check treats phrases that span paragraphs before the first scored run.
7. Optional: parent-level embeddings as an extra retrieval route (not part of the standard method).

#### Strategy 7 — Sentence window (concept learned; previewed on two questions; not built or scored)
*Written 2026-11-11. General-knowledge statements are marked; the preview is not an evaluation.*

**The problem it solves.** Same trade-off as parent-child: a single sentence is a precise search target, but a lone sentence is too little for the model to read. The sentence window keeps the precision and adds context.

**How it works**
1. **Split each paragraph into sentences** (the splitter matters even more here: everything is built from sentences).
2. **Embed every sentence on its own** and index those vectors.
3. **At question time, find the best matching sentences.**
4. **Expand each match into a window:** the matched sentence plus N sentences before and N after (N = 1 or 2, for example), so the model reads 2N + 1 sentences. Windows that overlap or touch are merged so the same sentences are not shown twice.
5. **Pass the windows to the model,** with the section, paragraph and page metadata of the match.

**How it differs from parent-child.** The context is a **sliding window centred on the match**, not a fixed parent passage. Its size is predictable (2N + 1 sentences), whereas a parent paragraph can be anything from a few hundred to over 10,000 characters. It needs no two-level structure: the neighbours can be looked up by sentence position, or the window text stored with each sentence (general knowledge: LlamaIndex stores the window in the sentence's metadata; not checked here). The cost is that the window ignores paragraph and speech boundaries unless we tell it to stop at them.

**What we measured and saw (2026-11-11; previews, not scores).** Setup as in the parent-child preview: spaCy rule-based splitter per paragraph, all 11,689 sentences embedded, five best matches per question, windows kept inside the paragraph. Working-set questions only.
- **R05 ("Who set fire to the Khandava forest, and why?").** Windows of 0, 1 and 2 sentences each side: **0 of 5 windows contained an evidence phrase** at every size, although the parent paragraph of the best match did (parent-child preview). So the evidence sentence is more than two sentences away from the best match: the window was too narrow here. Size of the five windows together: about 590 characters (N = 0), 1,625 (N = 1), 2,713 (N = 2); against about 15,000 characters for the five parents in the parent-child preview.
- **R15 ("Who is Sauti's father?").** 0 of 5 windows contained an evidence phrase at any size. The matches are the same tiny "Sauti said." fragments seen in the parent-child preview, so a window around a name-only match does not help (windows of 71 to 275 characters at N = 1).
- **Overlap.** The five matches came from five different paragraphs in both questions, so there were 0 overlapping window pairs; the duplicate-window problem did not show up in these two questions, but it would when matches cluster in one paragraph.
- **Evidence is sentence-sized.** Across the 24 working-set questions, 56 evidence phrases exist; **55 of the 56 lie fully inside one sentence** (spaCy rule-based split). So the best case is that the matched sentence is the right one and a small window adds context. Counting caveat: this depends on the splitter, and a phrase can be cut by it.
- **What the previews show:** a window gives a small, predictable context (hundreds of characters, not thousands), but it needs the match to land on or near the evidence; where the evidence is further away (R05) a parent catches it and a narrow window does not; and tiny name-only matches (R15) are as much a problem as in parent-child.

**Disadvantages**
1. **Child noise from tiny sentences,** the same R15 problem; the same minimum-size fix applies (merge sentences under a minimum length with the next).
2. **Window size is a guess.** Too narrow misses the evidence (R05), too wide brings back the budget and noise problems. Genealogy lists and speeches need different sizes.
3. **Overlapping and duplicate windows** when several matches cluster in one passage; windows must be merged.
4. **Windows ignore structure:** a window can end one speaker's words and start another's, and can cross a paragraph or section boundary unless told to stop.
5. **Total dependence on the sentence splitter.** There is no fallback to paragraph structure.
6. **About 11,689 vectors** against 1,670 baseline chunks, and the same scoring trap as parent-child: score the window text the model actually sees, and record the characters passed.

**How it would be built.** Our own code: split per paragraph with the chosen splitter, apply the minimum-size rule, embed the sentences (cached), keep each sentence's paragraph and position, expand a match into its window at query time, merge overlapping windows, and write the result in the baseline chunk format so downstream code is unchanged.

**Pending to experiment (sentence window):** none run yet; one variable at a time; after the splitter comparison.
1. Window size N: 0, 1, 2, 3 (with the splitter and minimum child size fixed).
2. Windows stay inside the paragraph, or may cross paragraphs within a section.
3. Minimum sentence size (none, 100, 200 characters).
4. Merging overlapping windows versus keeping them separate.
5. Record the characters passed to the model next to hit@5 and MRR@5; end-to-end correctness for the winner only.
6. Compare with parent-child on the same children: window versus paragraph parent.

#### Learning phase of the chunking stage: wrap-up (2026-11-11)
All seven strategies are now learned and logged: fixed (the baseline control), recursive, sentence-based, semantic, structure-aware, parent-child and sentence window. **Nothing is built or scored yet.**

**What the strategies have in common**
- **The sentence splitter is the shared dependency** for sentence-based, semantic, structure-aware (71% of the text is in long paragraphs), parent-child and sentence window. pySBD left 94 of the 452 long paragraphs unsplit (quote-pair rule); spaCy's rule-based splitter left none but cut after "viz."; NLTK and spaCy's parser mode are untested. **The splitter comparison therefore comes first.**
- **Tiny pieces match on names alone** (R15's "Sauti said." fragments), so any strategy with sentence-sized search units needs a minimum-size rule.
- **Context size is a budget:** paragraphs reach 10,838 characters, so any approach that hands whole paragraphs to the model needs a cap.
- **Score what the model sees,** and record the characters passed, so that bigger contexts do not win just because they contain more text.

**Suggested order for the experiments (a suggestion, the owner decides)**
1. Splitter comparison (pySBD with the quote fix, spaCy rule-based with an abbreviation fix; NLTK once its data is available).
2. Single-level strategies, retrieval metrics first: recursive (with a sentence-level separator), sentence-based, structure-aware, semantic.
3. Parent-child and sentence window on top of the best splitter and chunking result.
4. Judge scoring only for the likely winners; held-out only at a milestone.

**Decisions the owner still has to make:** which two or three strategies to build and compare; the splitter; whether chunks stay inside a paragraph; the first semantic breakpoint rule; size limits (see each strategy's "Pending to experiment" list).

#### Side-by-side
| Strategy | Respects sentences | Respects paragraphs and sections | Keeps the speaker | Extra cost | Main risk |
|---|---|---|---|---|---|
| Fixed | no | no | no | none | cuts anywhere |
| Recursive | only if a sentence separator is added | paragraphs yes | no | none | arbitrary packing; mid-sentence cuts by default |
| Sentence | yes | no | no | splitter | splitter errors; long sentences |
| Semantic | yes | no | no | embeds every sentence | unstable; threshold |
| Structure-aware | on long ones | yes | with a header | rules to tune | uneven sizes |
| Parent-child | child yes | via parent | via parent | extra lookup | duplicates; scoring |
| Sentence window | yes | no | partly | extra lookup | duplicates |

#### Alternatives and what comes next
Libraries mentioned are references only; no frameworks until Phase 4. **Next:** learn strategies 3 to 7 in the same detail as recursive, log each here, then choose which 2 or 3 to build and compare (the owner chooses). Before the first run, confirm that the retrieval scoring does not depend on chunk IDs (it checks the evidence phrase and the gold section), so results from different chunkings are comparable.

#### Gotchas so far
- I described the recursive ladder with a sentence level; the default has none. **Lesson:** test the library before describing its behaviour.
- My claim that leftovers do not merge was correct for this library; the owner's study notes said they can. **Lesson:** when two sources disagree, run the code.
- A pip-installed splitter can differ by version; the checks above were on `langchain-text-splitters` 1.1.3.

---

# Public post drafts
Written for a general audience (blog / LinkedIn). Numbers come from this project's Adi Parva corpus.

## Post 1 — Your RAG pipeline starts with cleaning, not embedding

I'm learning RAG by building one over the Mahabharata: Kisari Mohan Ganguli's English translation, starting with the Adi Parva. I'd read the usual advice: load, chunk, embed, retrieve. Then I looked at what I'd actually downloaded.

**The files are 99 MB. The story is 1.3 MB.** Each section is an HTML page, and only 1.4% of the characters are Mahabharata text. The rest is scripts, styling, sidebars and footers. A chunker doesn't know that. It sees a string and cuts it into windows. Feed it raw HTML and you'd build about 124,000 chunks instead of about 1,700, and almost all of them would be web markup. Every one gets embedded, stored and searched. Your top-5 results can end up being JavaScript.

Cleaning has to happen *before* chunking and embedding, as part of ingestion, because everything after it inherits its mistakes. Here is what mattered in practice:

- **The tempting shortcut is wrong.** The page's `<meta description>` holds a convenient text excerpt, but it's a truncated SEO summary that stops mid-sentence. It looks like text and isn't.
- **Scope the extraction.** Grabbing every `<p>` also picks up "No bookmarks yet" and the copyright footer. Only paragraphs inside the reader's article container are story.
- **Encoding silently corrupts names.** Reading UTF-8 files as latin-1 turns every apostrophe and dash into `â\x80\x99`. In a corpus where retrieval hinges on exact names, that's damage you won't notice until answers go wrong.
- **Page breaks split sentences.** Printed-page markers like `p. 16` fall in the middle of paragraphs. Chunk first and a speaker's "Sauti said…" ends up in one piece and the speech in another. About a third of the "paragraphs" on one page were really fragments. I glue them back using the site's own `[paragraph continues]` tag or a lowercase start after a marker, and I log every merge so I can eyeball them.
- **Test on everything, not three files.** My rules worked on the first three pages. The full run found a heading written `Section CLXXVI` instead of `SECTION CLXXVI`, and sub-section labels spelled three different ways for the same name. Without fixing those, a metadata filter would have silently dropped most of a section's text.

Two habits made this safe: **never modify the raw files** (cleaning writes to a separate folder, so I can re-run with new rules), and **keep provenance** (each paragraph carries its section, sub-parva and paragraph index, because citations depend on it later).

The takeaway: retrieval quality is capped by ingestion. No reranker or better embedding model rescues text you shouldn't have embedded in the first place. Before tuning anything, open your data and look at it.

## Post 2 — Measure your paragraphs before you pick a chunk size

"Chunk size 1000, overlap 200" is the default in half the tutorials. I wanted to know whether it fits my data instead of trusting it. So before writing a chunker, I measured the cleaned corpus: 1,306 paragraphs from the Adi Parva.

| | Characters |
|---|---|
| Median | 653 |
| Mean | 1,021 |
| 90th percentile | 2,334 |
| Longest | 10,838 |

The mean is far above the median, so the distribution has a long tail. 35% of paragraphs are longer than 1,000 characters and 31% are shorter than 400.

**Why this matters.** A fixed-size chunker ignores paragraph boundaries. A 10,000-character paragraph becomes a dozen chunks, and the speaker tag lives only in the first. A one-line reply embeds poorly on its own. Where the size lands decides how often each problem shows up. For 20% overlap, I computed how each size behaves:

| Chunk size | Chunks | Paragraphs that fit whole | Paragraphs needing 3+ chunks |
|---|---|---|---|
| 400 | ~4,200 | 31% | 33% |
| 600 | ~2,800 | 47% | 20% |
| 800 | ~2,100 | 57% | 12% |
| 1000 | ~1,700 | 65% | 8% |
| 1500 | ~1,100 | 79% | 2% |
| 2000 | ~800 | 87% | 1% |

**What the numbers say.** Below roughly 600, most paragraphs are cut apart, a third of them into three or more pieces. Above roughly 1,500, chunks mostly keep whole paragraphs but start mixing unrelated neighbours, and the many short paragraphs get swallowed. That brackets a sensible range of about 600 to 1,500.

**Why I'm starting at 1000/200.** It sits inside that range, so the stats don't argue against it. It's a round, widely used value, which makes my results easy to compare with other people's. It's also typically within the input limit of common embedding models, though limits vary by model and I'll check the one I choose. And 20% overlap is a conventional safety margin for facts that straddle a boundary.

**What the stats can't tell me.** They narrow the range but can't pick a winner. Whether 800 beats 1000 depends on how well each retrieves answers to real questions. So 1000/200 is a *hypothesis*, a baseline to beat, not a finding. Next I'll build a test set of questions and sweep the size one value at a time (600, 800, 1000, 1500), logging every result.

The general lesson: use data statistics to rule out bad settings and justify a starting point, then let evaluation make the final call.
