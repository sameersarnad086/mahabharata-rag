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
9. [Phase 1 retrospective (interim)](#phase-1-retrospective-interim)
10. [Public post drafts](#public-post-drafts)

---

## The pipeline at a glance

```
download  →  ingest/clean  →  chunk  →  embed  →  index  →  retrieve  →  generate answer
 (done)        (done)         (done:     (next)
                              baseline)
```

Rule of thumb I keep coming back to: **each stage can only pass on what the previous stage gave it.** A mistake in
ingestion is inherited by chunking, embedding and retrieval, and nothing later can repair it.

Current data flow and files (all derived data is gitignored and can be rebuilt with the scripts):

| Step | Input | Output | Script |
|---|---|---|---|
| Download | sacred-texts.com pages | `data/raw/.../section_001..237.html` (99 MB) | `scripts/download_adi_parva.py` |
| Ingest | raw HTML | `data/processed/paragraphs.jsonl` (1,306 paragraphs) | `scripts/run_ingest.py` |
| Check | paragraphs | sanity report | `scripts/report_ingest.py` |
| Chunk | paragraphs | `data/processed/chunks.jsonl` (1,670 chunks) | `scripts/run_chunking.py` |

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
- This is the domain challenge "many names for one person" in action. Candidate fixes for later: query rewriting that adds known aliases, a name-alias table, keyword search (BM25) combined with vectors (hybrid), or a knowledge graph (Phase 5).

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

---

## Known problems: where each one gets solved

The rule I follow: **measure a problem in Phase 2, mitigate it with a targeted technique in Phase 3, and only reach for
structural fixes (graphs, agents) in Phase 5 and 7 if the cheaper fixes are not enough.** Solving things in this order
means I can prove each fix helped, and I don't build a knowledge graph to fix something a keyword index would have fixed.

### 1. Many names for one person (Arjuna = Partha = Dhananjaya = Gudakesha; Krishna = Vasudeva = Keshava = Madhava)
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

## Phase 1 retrospective (interim)

**Rule (also in `CLAUDE.md`):** at the end of every phase I write a retrospective: what worked, what did not, how it
compares with standard RAG practice, and what that means for the next phase. This one is **interim**. It gets finalised
when Phase 1 ends, after retrieval and answer generation are built and I have run real questions end to end.

**Phase 1 still to do:** baseline retrieval module and command; answer generation with a language model (prompt
assembly, citations); a first set of end-to-end runs.

### What worked so far
- **Looking at the data before building.** Measuring the HTML (1.4% story text), the paragraphs (median 653 characters) and the token counts (max 399 vs a 512 limit) removed guesswork at three separate decisions.
- **Cleaning in ingestion with provenance kept.** Every chunk can be traced to its section, sub-parva, file and paragraph, which citations will need.
- **Reviewing small, then testing everything.** Checking three files by eye found the page-break problem; running all 237 found the heading-case and sub-parva-spelling bugs.
- **Caching with a fingerprint.** Re-running costs seconds, and a stale cache cannot be reused by accident.
- **One variable at a time, baseline first.** Plain fixed-size chunks plus a small local model gives me a number to beat.

### What did not work, or is weak so far
- **Aliases:** 0 of 5 overlap between "Arjuna" and "Partha" queries.
- **Ranking at the top is fragile:** top-5 scores sit within 0.02 of each other, and the passage with the actual vow ranked second for the celibacy question.
- **Fixed-size chunks cut mid-word** and 18% span more than one section.
- **`printed_page` is unreliable** and cannot be used in citations yet.
- **No quality numbers at all yet.** Everything above is observation from a handful of questions, not measurement.

### How this compares with standard RAG practice
| Standard practice | Where I am |
|---|---|
| Clean and parse the source properly before indexing | Done |
| Chunk by structure, not just by character count | Not yet; baseline is deliberately naive |
| Keep metadata on every chunk for filtering and citations | Done |
| Use hybrid search (keywords plus vectors) | Not yet |
| Rerank the shortlist | Not yet |
| Handle queries before retrieval (rewrite, expand, decompose) | Not yet |
| Build an evaluation set and metrics before tuning | **Not yet; this is the gap that matters most** |
| Ground answers, cite sources, and allow "I don't know" | Not yet (generation stage) |

### What this leads to
- **Phase 2 comes first, and it is measurement, not new techniques.** The evaluation set (with alias, multi-hop and unanswerable questions mixed in) turns today's impressions into numbers: recall@k, MRR, nDCG, faithfulness.
- **Phase 3 then follows the numbers.** The weakest metric tells me which stage to deepen first (probably query transformation and hybrid retrieval, given the alias result), one change at a time, logged in `EXPERIMENTS.md`.
- **Phases 4 to 7** only if the earlier fixes leave a measurable gap: framework comparison, advanced RAG, GraphRAG, and the lineage project.

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
