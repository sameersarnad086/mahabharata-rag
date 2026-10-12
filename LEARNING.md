# LEARNING.md — my RAG reference

Updated at the end of every meaningful step. Each entry: Concept / What we built / Alternatives / Gotchas.

## Phase 0 — Setup
**Concept:** A reproducible project skeleton: one config file, raw data cached on disk, metadata-first thinking.
**What we built:** `config.py`, `scripts/download_adi_parva.py`, folder layout (see README).
**Alternatives:** Project Gutenberg plain text (one big file, needs splitting by parva); sacred-texts HTML (already split into sections, which gives us section metadata for free).
**Gotchas:**
- Page numbers are offset: `m01001` is the Translator's Preface, `m01002` is Section I, so page = section + 1. Files are named `section_NNN.html` by *page*, so file 237 = Section CCXXXVI. Chunk metadata must use the real Roman-numeral section from the page title, not the file number, or every citation will be off by one.
- sacred-texts.com redirects `www.` to the bare domain; both hosts had to be allowed in the sandbox network policy.
- Raw pages are ~400 KB each (96 MB total) because they're full of site scripts/JSON; the actual text is a small fraction. Phase 1 ingestion must strip this, and the Sanskrit-name spelling in titles is Roman numerals.

## Phase 1 — Ingestion / cleaning (in progress; reviewed on files 001–003 only)
**Concept:** Chunking and embedding only see strings, so anything left in the text gets cut up and embedded. Ingestion turns raw HTML into clean paragraphs *with metadata* before any chunking. RAG quality is capped here: no later stage can fix embedded garbage.
**What we built:** [`src/rag/ingest.py`](src/rag/ingest.py) (`parse_file`) using BeautifulSoup with the stdlib `html.parser` backend; [`scripts/inspect_ingest.py`](scripts/inspect_ingest.py) prints extracted paragraphs and every page-break merge for eyeball review. Raw HTML is never modified.
**Alternatives:** stdlib `html.parser` alone (no dependency, but hand-written state tracking); `lxml` (faster, compiled extra, unnecessary at 237 small files); Project Gutenberg plain text (no HTML, but no per-section structure).
**Gotchas:**
- Raw pages are 99 MB but only 1.4% is story text (1.34 MB). Embedding raw HTML would mean ~124,000 chunks instead of ~1,700, mostly scripts and markup.
- The `<meta description>` / JSON-LD in `<head>` looks like text but is a truncated SEO summary. Never use it.
- Scope extraction to `<article data-slot="reader-content">`; a bare "all `<p>`" also grabs UI text ("No bookmarks yet", copyright footer).
- Read files as UTF-8. Reading as latin-1 turns `'` and `–` into mojibake (`â\x80\x99`), which would corrupt name matching.
- The `SECTION I` heading is in a `<div>`, not the `<h1>`, on file 002; heading detection must not assume `<h1>`.
- Page markers (`p. 16`, Roman `p. xii` in the preface) split paragraphs mid-sentence. Rule (Option A): glue a fragment back if it has the site's `[paragraph continues]` tag, or follows a page marker and starts lowercase. Roughly a third of "paragraphs" on file 003 were fragments before this.
- `printed_page` is approximate (preface numbering goes xii then ix; unclear if a marker means start or end of page). Do not use it in citations yet.
- Closing lines such as "Thus endeth the section called Parva-sangraha…" are kept as text.
- Source typos exist ("sixty-tour"); exact-match retrieval can't rely on clean spelling.

**Full-corpus run (all 237 files) — what the report found:**
- 1,306 paragraphs, 1.33 M chars, 385 page-break fragments merged. Output: `data/processed/paragraphs.jsonl` (gitignored; rebuild with `scripts/run_ingest.py`, check with `scripts/report_ingest.py`).
- Checking only 3 files was not enough: file 177 writes its heading as `Section CLXXVI` (mixed case), which silently broke the section sequence until the report flagged it. Always run a whole-corpus report.
- The sub-parva label appears on every section, not just the first, but spelled inconsistently (`Sambhava Parva`, `… continued`, `…, continued `). Normalised to 18 values; without that, a metadata filter on "Sambhava Parva" would miss most of its paragraphs. Same class of problem as Yudhishthira/Yudhisthira.
- Files 001–003 (preface, Sections I–II) have no sub-parva (`None`), which is expected. `Haranaharana Parva` looks odd but is probably genuine (not yet verified against the Parva-sangraha list).

## Phase 1 — Chunking (lesson; implementation not started)
**Concept:** An embedding model turns a piece of text into ONE vector. A whole section (thousands of words) averages many topics into a blurry vector, and the LLM's context window is limited, so we cut the corpus into chunks, embed each, and retrieve the best few. Chunk size is a trade-off:
- *Small chunks:* precise vectors, cheap context, but lost surroundings ("he then went to the forest" no longer says who "he" is).
- *Large chunks:* keep context, but blurrier vectors and more tokens spent per retrieved result.

**Baseline = fixed-size with overlap** (`CHUNK_SIZE`, `CHUNK_OVERLAP` in `config.py`): cut every N characters, overlapping neighbours so a fact straddling a boundary appears whole in at least one chunk. Weakness: it can cut mid-sentence or mid-name, e.g. "Santanu begat Bhishma on Ganga, and Vichi|travirya on Satyavati" leaves neither chunk with the full relationship. That is the lineage/multi-hop problem in miniature.

**Alternatives (each becomes its own one-variable experiment in Phase 3):**
| Method | Idea | Best when |
|---|---|---|
| Fixed-size | Cut every N chars, with overlap | Baseline, uniform text |
| Recursive | Split on paragraph, then sentence, then word, until under N | General-purpose default |
| Sentence-based | Group whole sentences up to N | Facts live inside single sentences |
| Semantic | Cut where adjacent-sentence embedding similarity drops | Topics shift unpredictably; costs embedding calls |
| Structure-aware | Cut on the source's own boundaries (paragraphs, speaker turns like "Sauti said…") | Text has real structure, as ours does |
| Parent-child | Embed small chunks, return the larger parent | Want precise matching AND rich context |

**Open decisions before implementing:** characters vs tokens (start with characters, test tokens as a separate experiment); whether chunks may cross paragraph boundaries (baseline: yes, pure fixed-size, so structure-aware is a measurable improvement later).

**Metadata on every chunk, from day one:** source, parva, real section number (Roman numeral from the page title, not the file number), sub-parva, paragraph index, character offsets. Citations depend on this.

**Data facts that shape chunking** (from `data/processed/paragraphs.jsonl`, 1,306 paragraphs): median 653 chars, mean 1,021, p90 2,334, p99 5,618, max 10,838. 35% of paragraphs exceed 1,000 chars; 31% are under 400. Long paragraphs get cut mid-thought (speaker tag only in the first piece); very short ones (one-line speech) embed poorly without neighbouring context.

**Domain flag:** chunking cannot fix aliases (Partha = Arjuna), but chunk size decides how much surrounding text carries identifying context.
**What we built:** [`src/rag/chunking.py`](src/rag/chunking.py): `fixed_size_spans()` (sliding window over character offsets), `build_chunks()` (joins all paragraphs into one string, cuts it, attaches metadata), `Chunk` dataclass. [`tests/test_chunking.py`](tests/test_chunking.py) has 9 edge-case checks; [`scripts/run_chunking.py`](scripts/run_chunking.py) writes `data/processed/chunks.jsonl`. Standard library only. Baseline run at 1000/200: 1,670 chunks, median length 1000, shortest 661 (the final tail).
**Gotchas:**
- The window must stop as soon as a chunk reaches the end of the text; otherwise the loop emits extra tail windows that add no new text.
- `overlap >= size` makes the step zero or negative and loops forever, so it must raise an error.
- Pure fixed-size cuts mid-word (chunk 500 starts `'e numerous. And…'`).
- 297 of 1,670 chunks (18%) span more than one section, so a chunk's metadata must be a list of sections, not a single value, or citations will be wrong.

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
