# LEARNING.md — my RAG notes

My personal reference for the Mahabharata RAG project. Written so I can re-read it months later and explain every
decision to someone else without opening the code. Updated at the end of every meaningful step.

Each stage follows the same layout: **Why it exists → What I decided (and why) → How it works → Tools used →
Alternatives → Gotchas → Results.**

**Contents**
1. [The pipeline at a glance](#the-pipeline-at-a-glance)
2. [Decisions log](#decisions-log)
3. [Phase 0 — Setup and download](#phase-0--setup-and-download)
4. [Phase 1 — Ingestion and cleaning](#phase-1--ingestion-and-cleaning)
5. [Phase 1 — Chunking](#phase-1--chunking)
6. [Phase 1 — Embeddings](#phase-1--embeddings)
7. [Phase 1 — Retrieval (concept)](#phase-1--retrieval-concept)
8. [Known problems: where each one gets solved](#known-problems-where-each-one-gets-solved)
9. [Phase 1 — Generation](#phase-1--generation)
   - [Question log: observed failures](#question-log-observed-failures-candidates-for-phase-2)
10. [Phase 1 retrospective (final)](#phase-1-retrospective-final)
11. [Phase 2 — Evaluation: concepts and metrics](#phase-2--evaluation-concepts-and-metrics)
12. [Public post drafts](#public-post-drafts)

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

*Status: concepts learned; retrieval question set (36) labelled with gold sections, evidence phrases and expected answers, checked by script; frozen working / held-out split; no metric code yet.*

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

### Decisions
Made: Claude drafts the questions and the user reviews them; the working / held-out split (24 / 12); approaches and goals above. Assumed unless the user objects: label by section **and** evidence phrase (both columns exist in the file). Done since: gold labels and evidence phrases for all 36 (above). Still open: whether the user adds questions of their own (a quarter of the set in their own words would be ideal; they would go in the separate "added" file).

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
