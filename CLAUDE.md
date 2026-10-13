# Mahabharata RAG — Learning Project

## Purpose
This is a **learning project first, a build project second.** I understand RAG at a high level
(from videos) and want to become an expert through hands-on implementation. Every stage of the
pipeline should be understood deeply, implemented by me, compared against alternatives, and measured.

The long-term goal: an AI system that explores the **Suryavamsha (Solar) and Chandravamsha (Lunar)
dynasties and their sub-lineages**, combining RAG over the source texts with a knowledge graph of
lineage relationships.

## How to work with me (important)
- **Teach before you build.** Before implementing any new stage or technique, explain the concept:
  what problem it solves, how it works, and the main alternatives with their trade-offs. Keep
  explanations concrete and tied to our Mahabharata data where possible.
- **I don't write code; I need to understand and explain it.** Claude writes all the code,
  including the core logic of each stage. I am not a coder, so explain in plain language, not
  code: which libraries and methods were used and why, how the technique works, the technical
  details and trade-offs, and what the results mean, so I can explain it to others. Mention any
  new library by name. Still review honestly and point out bugs, edge cases and better approaches.
- **One variable at a time.** When experimenting, change one thing, run the evaluation, and compare
  against the previous result. Don't bundle multiple changes into one experiment.
- **Ask, don't assume.** If a choice has real learning value (e.g. which embedding model to try
  next), present the options and let me decide.
- **Check for currency.** The RAG tool ecosystem moves fast. When we reach a stage, check whether
  newer libraries or models exist before recommending one.

## Learning doc — keep it updated
Maintain `LEARNING.md` as my personal RAG reference. Update it at the end of every meaningful step,
without being asked. For each concept or stage, add:
- **Concept** — what it is and why it matters, in plain language.
- **What we built** — summary with links to the relevant files/functions.
- **Alternatives** — other methods/tools and when each is better.
- **Gotchas** — mistakes I made or surprises we found.

At the end of every phase, add a **retrospective** to `LEARNING.md`: what worked, what didn't, how it
compares with standard RAG practice, and what it implies for the next phase.

Maintain `EXPERIMENTS.md` as an experiment log. One entry per experiment:
date, what changed, why, metrics before → after, and conclusion.

## Roadmap
- **Phase 0 — Setup.** Project structure, environment, download the Adi Parva (Ganguli translation).
- **Phase 1 — Naive RAG, no frameworks.** Load → fixed-size chunk → embed → numpy cosine top-k →
  LLM answer. Crude but working end to end. This is the baseline.
- **Phase 2 — Evaluation harness.** A test set of ~30–50 questions I write (with expected answers
  and source sections). Retrieval metrics (recall@k, MRR, nDCG) and generation metrics
  (faithfulness, answer relevance via LLM-as-judge). Implement them myself first, then compare with
  Ragas/DeepEval.
- **Phase 3 — Deep dive, one stage at a time.** For each: theory → my implementation → compare 2–3
  methods/tools → measure.
  - Ingestion & parsing
  - Chunking (fixed, recursive, sentence, semantic, structure-aware, parent-child)
  - Embeddings (several models; dense vs sparse/BM25)
  - Indexing (numpy brute force → FAISS Flat/IVF/HNSW → a vector DB)
  - Retrieval (top-k, MMR, metadata filters, hybrid with RRF)
  - Query transformation (rewriting, multi-query, HyDE, decomposition)
  - Reranking (cross-encoders, LLM rerankers)
  - Generation (prompt assembly, context ordering, citations, "I don't know" handling)
- **Phase 4 — Rebuild with a framework** (LlamaIndex or LangChain) and compare with my version.
- **Phase 5 — Advanced RAG.** Corrective RAG, Self-RAG, agentic RAG, and especially **GraphRAG**:
  LLM-extracted relationship triples → knowledge graph (networkx first, Neo4j later).
- **Phase 6 — Production concerns.** Latency, cost, caching, incremental re-indexing, tracing.
- **Phase 7 — Lineage project** (see below).

## Corpus
Start with the **Adi Parva** (most lineage-heavy), then scale to more parvas and texts.
All sources are public-domain English translations:
- **Mahabharata** — Kisari Mohan Ganguli translation (Project Gutenberg / sacred-texts.com).
- **Vishnu Purana** — H.H. Wilson translation (1840); Book IV lists both Solar and Lunar dynasties.
- **Harivamsha** — M.N. Dutt translation; Yadava lineage in depth.

## Conventions
- **Language:** Python. Keep dependencies minimal in Phases 1–3: no RAG frameworks until Phase 4.
- **Metadata from day one:** every chunk carries its source text, parva/book, section, and position.
  Accurate citations are essential for the lineage project.
- **Reproducibility:** configs (chunk size, model names, k, etc.) live in one place, not hard-coded.
  Cache embeddings to disk so experiments are cheap to rerun.
- **Don't modify the eval test set** to make results look better. Add new questions in a separate,
  clearly marked section.

## Domain challenges to keep in mind
These are known hard problems in this corpus. Point them out when they show up, as they are some
of the best learning moments:
- **Many names for one person:** Arjuna = Partha = Dhananjaya = Gudakesha; Krishna = Vasudeva =
  Keshava = Madhava.
- **Spelling variations** from Sanskrit transliteration (Yudhishthira / Yudhisthira).
- **Same name, different people:** multiple Parikshits and Janamejayas across generations.
- **Multi-hop questions:** e.g. how Krishna (Yadu line) and Arjuna (Puru line) are related through
  Yayati. No single passage answers this.
- **Conflicting sources:** different texts give different lineage lists. Report the disagreement
  with citations rather than silently picking one.

## Long-term vision: the lineage project
An explorer for the Suryavamsha and Chandravamsha lineages and sub-lineages:
- A **knowledge graph** of people and relationships (father/mother/son/spouse/descendant-of),
  every edge carrying its source citation.
- **Graph queries** for structure (ancestors, descendants, paths between two people, common ancestors).
- **RAG over the texts** for story context around each person and event.
- An **interactive family-tree visualization** with citations on every link.
- Explicit handling of name ambiguity and conflicting sources.
