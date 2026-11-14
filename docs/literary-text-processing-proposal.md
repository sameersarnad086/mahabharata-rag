# Exploring Domain-Aware Literary Text Processing for RAG
### An exploratory technical project proposal and brainstorming document

**Status:** Early-stage exploration  
**Origin:** Mahabharata RAG project  
**Potential direction:** Reusable, open-source NLP preprocessing toolkit for literary and narrative corpora

---

# 1. Background — Where the idea originated

While building the Mahabharata RAG application, I started exploring different chunking strategies to understand how source documents should be segmented before being embedded and indexed.

So far, the exploration has covered:

- Recursive character splitting.
- Sentence-aware chunking.
- Sentence boundary detection using PySBD, NLTK and spaCy.
- Semantic chunking using sentence embeddings and similarity scores.

An interesting observation emerged: the source corpus is not conventional modern prose.

It contains characteristics that could challenge general-purpose sentence splitters and conventional RAG preprocessing pipelines:

- Multiple names and epithets for the same character.
- Sanskrit-derived names and transliterations.
- Older English translation conventions.
- Long, compound sentences.
- Extensive genealogy and relationship descriptions.
- Repeated conjunctions and unusual punctuation.
- Dialogue and changes in speakers.
- Pronouns and references whose meaning depends on previous sentences.
- Narrative continuity that may not be captured by sentence-level semantic similarity.

For example, Arjuna may be referred to as Arjuna, Partha, Dhananjaya or Phalguna. These names can refer to the same character, but a general-purpose sentence splitter does not know that.

Similarly, consider these two sentences:

"These eight are known as the Vasus."

"Of these, Dhara and the truth-knowing Dhruva were born of Dhumra."

An embedding-based semantic chunker might identify a relatively low similarity between these sentences. However, the second sentence directly elaborates on the first.

This raises a broader question:

**Are general-purpose NLP preprocessing tools sufficient for literary and narrative corpora, or could domain-adapted preprocessing improve the quality of RAG systems?**

That is the starting point of this project.

---

# 2. The opportunity

The initial idea is to investigate whether we can build a reusable preprocessing toolkit specifically designed for literary, historical, mythological and narrative texts.

The ambition is not necessarily to build another sentence splitter.

It is to understand whether the linguistic and structural characteristics of these documents require additional preprocessing capabilities before they enter a RAG pipeline.

A possible project direction:

**Domain-Aware Literary Text Processing for RAG**

The toolkit could eventually help developers process:

- Historical literature.
- Mythological texts and epics.
- Translated novels.
- Religious and philosophical texts.
- Classical literature.
- Historical archives.
- Narrative-heavy documents.

The Mahabharata would serve as the initial development and evaluation corpus, rather than being the only intended use case.

## Why this might be useful

Most conventional RAG pipelines follow a relatively straightforward sequence:

1. Load documents.
2. Split documents into chunks.
3. Generate embeddings.
4. Store vectors.
5. Retrieve relevant chunks.

However, the quality of the resulting chunks depends heavily on the characteristics of the source document.

A modern technical article, a legal document and a translated epic do not necessarily have the same structural requirements.

The opportunity is to investigate whether preprocessing should be adapted to the nature of the source material.

---

# 3. Three distinct technical problems

One important conclusion from the initial discussion is that several different NLP problems are involved.

They should not be treated as one problem or solved using a single model.

## A. Sentence boundary detection

**Problem:** Determining where a sentence starts and ends.

Example:

"Mr. Sameer was studying the Mahabharata. He was particularly interested in Arjuna's story."

A naive full-stop splitter might incorrectly split after "Mr."

Potential approaches:

- Rule-based segmentation.
- Statistical sentence tokenization.
- Domain-specific abbreviation dictionaries.
- Custom sentence-boundary models.
- Fine-tuned NLP models.

Potential objective:

Improve sentence segmentation accuracy on historical and literary English text.

## B. Entity and alias resolution

**Problem:** Identifying different names and expressions that refer to the same entity.

Example:

| Mention | Canonical entity |
|---|---|
| Arjuna | Arjuna |
| Partha | Arjuna |
| Dhananjaya | Arjuna |
| Phalguna | Arjuna |
| Son of Pandu | Arjuna, where context supports it |

This is not a sentence-splitting problem.

It involves named entity recognition, entity linking and alias resolution.

There is also a contextual disambiguation problem: an epithet or relationship-based reference should not automatically be mapped to an entity without sufficient evidence.

Potential objective:

Create a domain-aware entity dictionary and investigate whether entity-aware preprocessing improves retrieval.

## C. Narrative and contextual continuity

**Problem:** Preserving relationships between sentences that belong together conceptually.

Example:

"These eight are known as the Vasus."

"Of these, Dhara and the truth-knowing Dhruva were born of Dhumra."

A similarity-based chunker might identify a lower similarity score between these sentences, even though they are narratively connected.

Other examples:

- A sentence introduces a character; the next explains their parentage.
- A sentence introduces a speaker; the next contains their dialogue.
- A sentence describes an event; the next explains its consequence.
- A sentence uses a pronoun whose antecedent appears in the previous sentence.

Potential approaches:

- Rolling-window semantic similarity.
- Entity-aware chunking.
- Coreference resolution.
- Paragraph and section boundary signals.
- Narrative relationship detection.
- Custom chunk-boundary rules.

Potential objective:

Improve the contextual completeness of retrieved chunks without unnecessarily increasing their size.

---

# 4. Proposed technical architecture

The following is a conceptual architecture, not a decision to implement every component.

## Literary Text Processing Toolkit

### Stage 1 — Input and document structure

Accept source documents and preserve their original structure.

Possible inputs:

- Plain text.
- Markdown.
- HTML.
- Structured JSON.
- Documents with section and paragraph metadata.

Preserve source provenance wherever possible.

### Stage 2 — Sentence segmentation

Identify sentence boundaries using configurable segmentation engines.

Potential components:

- PySBD.
- NLTK Punkt.
- spaCy dependency parser.
- spaCy Sentencizer.
- Custom rule-based segmenter.
- Domain-adapted segmentation model.

The first research question is whether a custom approach can outperform existing tools on literary text.

### Stage 3 — Entity and alias identification

Identify character names, locations, objects and other relevant entities.

Potential components:

- Domain dictionaries.
- Named entity recognition.
- Alias resolution.
- Entity linking.
- Contextual disambiguation.

Example:

Arjuna → Partha → Dhananjaya → Phalguna.

The system should preserve the original mention while optionally associating it with a canonical entity ID.

### Stage 4 — Contextual and narrative analysis

Investigate relationships between sentences.

Potential capabilities:

- Pronoun and reference resolution.
- Speaker identification.
- Character relationship extraction.
- Event continuity.
- Narrative dependency identification.

This could help identify sentences that should remain together even when their embedding similarity is relatively low.

### Stage 5 — Semantic segmentation

Identify topic transitions and candidate chunk boundaries.

Potential techniques:

- Adjacent-sentence cosine similarity.
- Rolling-window similarity.
- Similarity distribution and breakpoint detection.
- Entity continuity signals.
- Paragraph and section boundaries.
- Semantic clustering.

The objective is to combine semantic similarity with additional structural evidence.

### Stage 6 — Chunk constraints and output

Apply configurable constraints:

- Minimum chunk size.
- Maximum chunk size.
- Token or character limits.
- Sentence overlap.
- Paragraph preservation.
- Section boundaries.
- Metadata and source provenance.

The final output should be suitable for downstream embedding and vector indexing.

---

# 5. Research area 1 — Domain-specific sentence segmentation

This is the most logical starting point.

Before developing a custom model, establish how existing tools perform on the corpus.

## Existing approaches to benchmark

| Tool | Approach | What to investigate |
|---|---|---|
| PySBD | Rule-based | How well its rules handle historical prose and unusual punctuation |
| NLTK Punkt | Statistical, unsupervised | Pretrained versus corpus-trained parameters |
| spaCy dependency parser | Syntactic NLP model | Whether syntactic context improves boundary detection |
| spaCy Sentencizer | Rule-based | Lightweight punctuation-based segmentation |
| Custom implementation | Rules or trained model | Whether domain-specific adaptation improves accuracy |

## Possible research questions

1. Do general-purpose English sentence splitters perform poorly on translated epic literature?
2. Which types of passages generate the most segmentation errors?
3. Can a domain-specific abbreviation and punctuation dictionary improve performance?
4. Does training Punkt on the target corpus improve segmentation?
5. Does a dependency parser perform better on long, compound sentences?
6. Can a small custom model outperform existing libraries?

## Dataset requirements

Create a manually verified evaluation dataset.

A starting target could be 100–200 passages representing different writing characteristics.

Include:

- Genealogical descriptions.
- Dialogue.
- Long compound sentences.
- Abbreviations and initials.
- Semicolon-heavy passages.
- Unusual punctuation.
- Character introductions.
- Narrative transitions.

For each passage, manually annotate the correct sentence boundaries.

This becomes the ground truth against which different approaches can be evaluated.

## Evaluation metrics

| Metric | What it measures |
|---|---|
| Boundary precision | How many predicted boundaries are correct |
| Boundary recall | How many actual boundaries were detected |
| Boundary F1 | Balance between precision and recall |
| False splits | One sentence incorrectly split into multiple sentences |
| Missed splits | Multiple sentences incorrectly joined |

A particularly useful addition would be error categorisation.

Instead of only knowing that a splitter failed, record why:

- Abbreviation error.
- Quotation error.
- Initial detection error.
- Decimal or numerical punctuation error.
- Compound sentence error.
- Historical punctuation error.

This could eventually become a reusable literary segmentation benchmark.

---

# 6. Research area 2 — Domain-specific entity recognition

This is a potentially valuable extension.

The Mahabharata contains many entities with multiple names and epithets.

For example, a character may be referenced through:

- Their given name.
- Their lineage.
- Their place of origin.
- Their relationship to another character.
- Their accomplishments.
- Their title or epithet.

A conventional entity recognition model may recognise some names but fail to associate all references with the same entity.

## Possible implementation stages

**Stage 1: Domain dictionary**

Build a canonical entity registry.

Example:

| Entity ID | Canonical name | Known aliases |
|---|---|---|
| E001 | Arjuna | Partha, Dhananjaya, Phalguna |
| E002 | Krishna | Vasudeva, Keshava, Madhava |
| E003 | Bhima | Vrikodara, Bhimasena |

These are illustrative mappings. Actual mappings must be verified against the source and context.

**Stage 2: Entity recognition**

Identify entity mentions in each sentence.

**Stage 3: Alias resolution**

Associate a mention with a canonical entity ID where the evidence supports it.

**Stage 4: Contextual disambiguation**

Avoid mapping ambiguous expressions automatically.

For example, "son of Pandu" can be ambiguous because Pandu has multiple sons.

## Potential RAG benefit

A retrieval system could potentially use entity metadata to improve retrieval when a question uses an alias different from the one used in the source passage.

This is a separate hypothesis that needs evaluation.

---

# 7. Research area 3 — Narrative-aware chunking

This is perhaps the most interesting research direction from the original chunking exploration.

Conventional semantic chunking commonly uses sentence embeddings and similarity scores.

A simplified approach:

1. Split the text into sentences.
2. Generate embeddings for each sentence.
3. Compare adjacent sentence embeddings.
4. Identify similarity drops.
5. Create candidate chunk boundaries.

However, similarity does not necessarily represent narrative continuity.

## The Vasu genealogy example

Sentence A:

"These eight are known as the Vasus."

Sentence B:

"Of these, Dhara and the truth-knowing Dhruva were born of Dhumra."

The sentences may have a relatively low cosine similarity.

But Sentence B is explicitly elaborating on the group introduced in Sentence A.

A more sophisticated approach could consider multiple signals:

| Signal | What it contributes |
|---|---|
| Sentence similarity | Semantic relatedness |
| Entity continuity | Whether the same characters or entities appear |
| Reference continuity | Whether a sentence refers to something introduced earlier |
| Paragraph structure | Whether sentences belong to the same paragraph |
| Narrative relationships | Whether one sentence elaborates on or continues another |
| Section metadata | Whether sentences belong to the same source section |

A future chunking algorithm could combine these signals to make boundary decisions.

For example, a low similarity score might suggest a boundary, but strong reference continuity could reduce the likelihood of splitting.

This is only a proposed direction. It would require a defined scoring mechanism and an annotated evaluation dataset.

---

# 8. Should we fine-tune or customise?

Do not begin with fine-tuning.

There are several levels of adaptation, each with different complexity.

| Level | Approach | Complexity |
|---|---|---|
| 1 | Custom punctuation and abbreviation rules | Low |
| 2 | Domain-specific dictionaries and metadata | Low–medium |
| 3 | Train Punkt on the target corpus | Medium |
| 4 | Train or fine-tune an NLP model for sentence segmentation | High |
| 5 | Fine-tune an entity recognition or resolution model | High |
| 6 | Develop narrative-aware segmentation | Very high |

These are separate model and engineering problems.

For instance:

- Sentence segmentation training requires sentence-boundary annotations if using a supervised approach.
- Entity recognition requires entity-labelled text.
- Entity resolution requires canonical entity identities and mention mappings.
- Narrative-aware chunking requires annotations describing which sentences should remain together or where coherent boundaries occur.

A fine-tuned model should be justified by measurable improvements over simpler methods.

---

# 9. Proposed first experiment

Rather than developing the entire toolkit, begin with a focused benchmark.

## Milestone 1 — Literary Sentence Segmentation Benchmark

**Objective:** Determine whether domain-specific adaptation improves sentence-boundary detection.

### Scope

- Select 100–200 representative passages.
- Manually annotate sentence boundaries.
- Run the same passages through multiple segmentation approaches.
- Compare the results.
- Categorise errors.
- Identify whether a custom approach is justified.

### Candidate configurations

1. PySBD.
2. NLTK pretrained Punkt.
3. NLTK Punkt trained on the corpus.
4. spaCy dependency parser.
5. spaCy Sentencizer.
6. Custom rule-based approach.

### Expected outputs

- Annotated evaluation dataset.
- Benchmark scripts.
- Accuracy and error analysis.
- Comparison report.
- Initial recommendations for domain adaptation.

### Success criteria

The first milestone should establish:

1. Whether general-purpose tools have meaningful limitations on this corpus.
2. Which types of linguistic patterns cause failures.
3. Whether a relatively simple custom approach improves accuracy.
4. Whether improvements are significant enough to justify further development.

Do not assume that a custom solution will win. A useful research result could also be that an existing tool performs sufficiently well.

---

# 10. Beyond segmentation — Measuring actual RAG improvements

Sentence-boundary accuracy is not the final objective.

The eventual reason to improve preprocessing is to improve retrieval and answer quality.

A splitter could produce perfectly segmented sentences but still generate poor RAG chunks.

Therefore, a later experiment should compare:

- Recursive character chunking.
- Sentence-aware chunking.
- Standard semantic chunking.
- Domain-adapted semantic chunking.

Keep the embedding model, retrieval configuration and evaluation questions consistent.

Possible evaluation dimensions:

| Metric | What it evaluates |
|---|---|
| Retrieval precision | How many retrieved chunks are relevant |
| Retrieval recall | Whether the relevant evidence is retrieved |
| Context completeness | Whether retrieved chunks contain sufficient supporting context |
| Answer faithfulness | Whether generated answers are supported by retrieved evidence |
| Citation accuracy | Whether the answer points to the correct source passage |

For the Mahabharata project, source-grounded answer evaluation and section-level citation accuracy are especially relevant.

This gives the research a more meaningful outcome than simply optimising chunk size.

---

# 11. Open-source potential

If the experiments show meaningful improvements, the work could become a reusable open-source toolkit.

A possible positioning:

**Literary NLP preprocessing for RAG systems.**

Potential users:

- Developers building RAG applications over classical literature.
- Researchers working with historical texts.
- Developers working with mythology and religious literature.
- Digital humanities projects.
- Teams processing translated narrative documents.

Possible components:

- Configurable sentence segmentation.
- Domain-specific abbreviation dictionaries.
- Entity alias registries.
- Narrative-aware chunking experiments.
- Metadata and provenance preservation.
- Evaluation benchmarks.
- Integrations with LangChain and other RAG frameworks.

The project should not be positioned as a universal solution for all literary languages from day one.

Start with English-language translated literary texts, document the limitations and expand based on evidence.

Also, verify the licensing of source translations before distributing corpus material. An open-source implementation and annotation framework can be distributed separately from copyrighted source text.

---

# 12. Risks and open questions

Several questions remain unresolved.

### Technical risks

- Existing splitters may already perform adequately.
- Corpus-specific rules may overfit to the Mahabharata translation.
- Alias resolution can introduce incorrect entity associations.
- Semantic similarity may be a weak signal for narrative continuity.
- Narrative-aware approaches may require expensive manual annotation.
- Improvements in segmentation may not translate into better retrieval.

### Scope risks

The project could become too broad if sentence segmentation, entity resolution, coreference, semantic chunking and narrative understanding are developed simultaneously.

The initial scope should remain narrow.

### Research questions to revisit

1. Is the primary problem sentence segmentation or contextual chunk formation?
2. How representative is the Mahabharata corpus of other literary texts?
3. Should the first deliverable be a benchmark, a library or a trained model?
4. What level of domain adaptation produces measurable improvements?
5. Can entity metadata improve retrieval without modifying the underlying text?
6. Can narrative continuity be evaluated consistently by human annotators?
7. What is the smallest useful open-source release?

---

# 13. Current working hypothesis

The working hypothesis is:

**General-purpose NLP preprocessing methods may not adequately capture the linguistic and narrative characteristics of certain literary corpora. Domain-aware preprocessing, combining sentence-boundary detection, entity information, structural metadata and semantic signals, may produce more coherent chunks and improve downstream RAG retrieval.**

This is a hypothesis to test, not an established conclusion.

The project should be evidence-led.

---

# 14. Suggested roadmap

| Phase | Focus | Deliverable |
|---|---|---|
| 1 | Understand corpus characteristics | Corpus profiling and error taxonomy |
| 2 | Benchmark sentence splitters | Annotated dataset and comparison |
| 3 | Test domain adaptation | Custom rules or trained segmentation |
| 4 | Explore entity and alias resolution | Entity registry and prototype |
| 5 | Explore narrative-aware chunking | Experimental chunking algorithm |
| 6 | Evaluate downstream RAG | Retrieval and answer-quality comparison |
| 7 | Generalise and package | Open-source toolkit and documentation |

Phases 3–7 should depend on the findings of earlier phases, rather than being treated as a committed implementation plan.

---

# 15. Brainstorming notes — To continue later

The following are decisions that remain open.

**Project positioning**
- [ ] Literary NLP preprocessing toolkit.
- [ ] Domain-adapted RAG preprocessing framework.
- [ ] Research project on narrative-aware chunking.
- [ ] A combination of the above.

**Initial technical scope**
- [ ] Sentence segmentation only.
- [ ] Sentence segmentation plus entity recognition.
- [ ] Sentence segmentation plus semantic chunking.
- [ ] Full narrative-aware preprocessing.

**Initial corpus**
- [ ] Mahabharata English translation.
- [ ] Additional public-domain epics.
- [ ] Other historical or translated literature.

**Implementation direction**
- [ ] Rule-based customisation.
- [ ] Statistical adaptation.
- [ ] Fine-tuning.
- [ ] Hybrid approach.

**Evaluation**
- [ ] Sentence-boundary benchmark.
- [ ] Entity-resolution benchmark.
- [ ] Chunk-coherence evaluation.
- [ ] Downstream RAG retrieval evaluation.

---

# Final perspective

The most valuable aspect of this idea is not necessarily developing a new sentence splitter.

It is investigating a broader engineering question:

**Should the preprocessing strategy of a RAG system be determined by the linguistic and structural characteristics of its source corpus?**

The Mahabharata project gives us a practical environment to investigate that question.

Start with a measurable problem, build a benchmark, compare existing approaches and only then decide whether a new model or toolkit is warranted.

If the findings are strong, the work could evolve into a reusable open-source project that benefits developers working with literary and narrative corpora.

For now, this remains an exploration worth pursuing, not an implementation commitment.