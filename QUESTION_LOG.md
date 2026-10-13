# QUESTION_LOG.md

Informal questions asked of the Phase 1 baseline, with the full result and a human verdict.
These are exploration notes, **not** the Phase 2 evaluation set (which is written separately and never edited to flatter results).

Questions Q1 to Q5 mainly illustrate the **lineage and one person with more than one name problem** (see `LEARNING.md`, "Named problems").

Setup for all entries: fixed-size chunks (1000 chars, 200 overlap), `BAAI/bge-small-en-v1.5` embeddings, top-5 cosine retrieval,
`gemini-3.1-flash-lite` (temperature 0). Section numbers are the printed heading numbers; the file name is always heading + 1.
Chunk ids are positions in `data/processed/chunks.jsonl` and change if chunking changes.


## Q1. Why did Bharata grow up away from his father?
_Run on 2026-10-13_

**Answer given:**

> The provided passages do not answer this question. The passages discuss the upbringing of the sons of Pandu in their father's home and the birth of Bhima and Duryodhana, but they do not mention a person named Bharata growing up away from his father.

Tokens: prompt 1562, output 53. Citations in answer: none

**Top-5 chunks retrieved:**

1. score 0.704 | chunk 976 | Section 128 (Sambhava Parva) | `section_129.html` para 2 | not cited
   - starts: "Ambika, I hear that in consequence of the deeds of your grandsons, this Bharata dynasty and its subjects will perish. If thou permit, I would go to the forest with Kausalya, so grieved at th..."
2. score 0.693 | chunk 940 | Section 123 (Sambhava Parva) | `section_124.html` para 1 | not cited
   - starts: "endued with strength.' I must tell you, O Bharata, of another wonderful event that occurred alter the birth of Vrikodara (Bhima). While he fell from the lap of his mother upon the mountain b..."
3. score 0.687 | chunk 1385 | Section 191, 192 (Swayamvara Parva) | `section_192.html` para 1 | not cited
   - starts: "ittle before, left the amphitheatre, is Dharma's son (Yudhishthira). The two other youths, like unto Kartikeya, are, I suspect, the sons of the twin Aswins. I heard that the sons of Pandu al..."
4. score 0.682 | chunk 987 | Section 129 (Sambhava Parva) | `section_130.html` para 3 | not cited
   - starts: "her eldest son, she summoned Vidura, and said, 'O illustrious Kshattri , Bhimasena is missing! Where has he gone? The other brothers have all come back from the gardens, only Bhima of mighty..."
5. score 0.679 | chunk 862 | Section 110, 111 (Sambhava Parva) | `section_111.html` para 1 | not cited
   - starts: "bestowed his sister along with many valuable robes, and having received Bhishma's adorations, returned to his own city. And, O thou of Bharata's race, the beautiful Gandhari gratified all th..."

**Verdict:** RETRIEVAL MISS, correct refusal. The book covers this (Dushmanta's son by Sakuntala, raised in Kanwa's hermitage, Section 74), but none of the five chunks is about it. Recall@5 = 0. Explainable, fixable later.

**Notes:** Where the relevant text ranked out of 1,670 chunks: chunk 580 (Section 74, boy named Sarvadamana in the hermitage) 351st; chunk 600 (Section 74, 'known by the name of Bharata, the cherished') 133rd; chunks 543/544 (Sections 68-69, Janamejaya asks about Bharata's birth and life) 694th/731st. The word 'Bharata' appears in 255 of 1,670 chunks, mostly as a form of address ('O Bharata'). Hypotheses: alias (Sarvadamana), same word with different meanings, question words resembling generic upbringing passages, story spread over Sections 69-74, dense retrieval scores meaning not exact words.

---

## Q2. Who was the father of Pandu?
_Run on 2026-10-13_

**Answer given:**

> The provided passages do not answer this question. The passages discuss Pandu's children, his death, and the history of his race, but they do not name his father.

Tokens: prompt 1534, output 36. Citations in answer: none

**Top-5 chunks retrieved:**

1. score 0.749 | chunk 967 | Section 126 (Sambhava Parva) | `section_127.html` para 2 | not cited
   - starts: "orld, repaired hence to dwell on the mountain of a hundred peaks. He adopted the Brahmacharya mode of life, but for some inscrutable purpose the gods have in view, this his eldest son, Yudhi..."
2. score 0.742 | chunk 1543 | Section 217 (Arjuna-vanavasa Parva) | `section_218.html` para 0 | not cited
   - starts: " Pandu and Kunti.' The king, hearing this, spoke unto him these words in sweet accents, 'There was in our race a king of the name of Prabhanjana, who was childless. To obtain a child, he und..."
3. score 0.742 | chunk 879 | Section 113, 114 (Sambhava Parva) | `section_114.html` para 1 | not cited
   - starts: "ing many hostile kingdoms, wept tears of joy. And Pandu, instilling joy into the hearts of his people with a flourish of trumpets and conchs and kettle-drums, entered his capital.'" "Vaisamp..."
4. score 0.714 | chunk 968 | Section 126 (Sambhava Parva) | `section_127.html` para 2 | not cited
   - starts: " Pandu, will, no doubt, give you great pleasure. Steadily adhering to the path of the virtuous and the wise, and leaving behind him these children, Pandu departed hence seventeen days ago. H..."
5. score 0.709 | chunk 938 | Section 123 (Sambhava Parva) | `section_124.html` para 0 | not cited
   - starts: "ed to acquire a great fame, at the eighth Muhurta called Abhijit , of the hour of noon of that very auspicious day of the seventh month (Kartika), viz ., the fifth of the lighted fortnight, ..."

**Verdict:** RETRIEVAL MISS, correct refusal. The answer is in Section 106 (Krishna-Dwaipayana begot Pandu on Ambalika) but no chunk from it is in the top 5.

**Notes:** Section 106 chunks ranked: chunk 846 46th, chunk 844 68th, chunk 845 176th. Results 1 and 4 are neighbouring overlapping chunks from the same place (Section 126), so two of the five slots are near-duplicates. The question is subtle in the text too: nominal father Vichitravirya vs biological father Vyasa.

---

## Q3. Who is the father of Arjuna?
_Run on 2026-10-13_

**Answer given:**

> Arjuna is the son of Pandu [4][5]. Additionally, he is described as the son of Indra [3].

Tokens: prompt 1573, output 26. Citations in answer: [4, 5, 3]

**Top-5 chunks retrieved:**

1. score 0.717 | chunk 1023 | Section 134 (Sambhava Parva) | `section_135.html` para 2 | not cited
   - starts: "hed vessel with water by means of the Varuna weapon he used to come unto his preceptor at the same time with his preceptor's son. And accordingly the intelligent son of Pritha, that foremost..."
2. score 0.713 | chunk 1629 | Section 229 (Khandava-daha Parva) | `section_230.html` para 0 | not cited
   - starts: "ke arrows. The celestials repeatedly routed by Krishna and Arjuna, at last left the field of battle for fear and sought the protection of Indra. The Munis who were witnessing the battle from..."
3. score 0.709 | chunk 531 | Section 67 (Sambhava Parva) | `section_068.html` para 5 | **CITED**
   - starts: "y son. He is dearer to me than life itself. Let this be the compact and let it be not transgressed. The destruction of the Asuras on earth is the work of the celestials, and, therefore, it i..."
4. score 0.706 | chunk 754 | Section 95 (Sambhava Parva) | `section_096.html` para 8 | **CITED**
   - starts: "king of Kasi, offered his own prowess as dower and begat upon her a son named Sarvaga. And Arjuna also, repairing to Dwaravati, brought away by force Subhadra. the sweet-speeched sister of V..."
5. score 0.705 | chunk 1542 | Section 217 (Arjuna-vanavasa Parva) | `section_218.html` para 0 | **CITED**
   - starts: "he Mahendra mountain adorned with the ascetics (residing there), he went to Manipura, proceeding slowly along the sea-shore. Beholding all the sacred waters and other holy places in that pro..."

**Verdict:** RIGHT ANSWER, one unsupported citation. 'Son of Pandu' is supported by [5] and [3]; 'son of Indra' by [3] ('born as Indra's son and known as Arjuna, the mighty son of Pandu'). Citation [4] (about Subhadra) supports neither claim.

**Notes:** The citation checker only verifies that a cited number exists; it passed [4]. Judging whether a cited passage supports the claim is the Phase 2 faithfulness measure. Passage [5] also contains Arjuna saying 'I am Dhananjaya, the son of Pandu and Kunti', so the text itself uses aliases.

---

## Q4. Who is the father of Partha?
_Run on 2026-10-13_

**Answer given:**

> The provided passages do not answer this question. The passages discuss the lineage of the Vasus, the descendants of Tansu, and the story of King Kalmashapada and the Rishi Saktri.

Tokens: prompt 1659, output 41. Citations in answer: none

**Top-5 chunks retrieved:**

1. score 0.682 | chunk 502 | Section 66 (Sambhava Parva) | `section_067.html` para 0 | not cited
   - starts: "cred vows, are employed in indicating time; and they are the Nakshatras and the Yoginis and they became so for assisting the courses of the worlds. "And Brahman had another son named Manu. A..."
2. score 0.677 | chunk 503 | Section 66 (Sambhava Parva) | `section_067.html` para 1 | not cited
   - starts: "estroyer of the worlds. And Soma's son is the resplendent Varchas. And Varchas begot upon his wife Manohara three sons--Sisira, and Ramana. And the son of Aha were Jyotih, Sama, Santa, and a..."
3. score 0.675 | chunk 1328 | Section 180 (Chaitraratha Parva) | `section_181.html` para 0 | not cited
   - starts: "him with tearful eyes and said, 'O child, do not address this thy grandfather as father ? Thy father, O son, has been devoured by a Rakshasa in a different forest. O innocent one, he is not ..."
4. score 0.669 | chunk 1309 | Section 178 (Chaitraratha Parva) | `section_179.html` para 0 | not cited
   - starts: "ued, 'There was, O Partha, a king in this world, named Kalmashapada, who was of the race of Ikshvaku and was unequalled on earth for prowess. One day the king went from his capital into the ..."
5. score 0.664 | chunk 745 | Section 95 (Sambhava Parva) | `section_096.html` para 2 | not cited
   - starts: "and. And he begat upon her a son named Tansu. Here occurs a sloka descriptive of Tansu's descendants. "Tansu was born of Saraswati by Matinara. And Tansu himself begat a son named Ilina on h..."

**Verdict:** RETRIEVAL MISS, correct refusal. Same fact as Q3, but the question uses the name 'Partha' and none of the five chunks is relevant (Vasus, Tansu's descendants, Kalmashapada).

**Notes:** Q3 vs Q4 is the cleanest alias demonstration so far: the same question with two names for the same person gives an answer for one and a refusal for the other. Phase 3 fixes: alias expansion of the query, keyword plus meaning search, later a people graph.

---

## Q5. How are Krishna and Arjuna related through Yayati?
_Run on 2026-10-13_

**Answer given:**

> The provided passages do not answer this question. The passages cover the identities, divine origins, and exploits of Krishna and Arjuna, but they do not mention Yayati.

Tokens: prompt 1599, output 33. Citations in answer: none

**Top-5 chunks retrieved:**

1. score 0.704 | chunk 1369 | Section 189 (Swayamvara Parva) | `section_190.html` para 0 | not cited
   - starts: "nd the Adityas, the Vasus and the twin Aswins, the Swadhas and all the Marutas, and Kuvera with Yama walking ahead. And there came also the Daityas and the Suparnas, the great Nagas and the ..."
2. score 0.695 | chunk 1437 | Section 199 (Vaivahika Parva) | `section_200.html` para 3 | not cited
   - starts: "ite. And those two hairs entered the wombs of two of the Yadu race, by name Devaki and Rohini. And one of these hairs viz ., that which was white, became Valadeva. And the hair that was blac..."
3. score 0.690 | chunk 443 | Section 61 (Adivansavatarana Parva) | `section_062.html` para 4 | not cited
   - starts: " numerous evils, the Pandavas gradually rose to power. And Bhima of great reputation subjugated the East, the heroic Arjuna, the North, Nakula, the West; Sahadeva that slayer of all hostile ..."
4. score 0.683 | chunk 1633 | Section 230 (Khandava-daha Parva) | `section_231.html` para 0 | not cited
   - starts: "ld vanquish in battle Krishna and Arjuna. When the celestials saw that they could not protect that forest from the might of Krishna and Arjuna by extinguishing that conflagration, they retir..."
5. score 0.678 | chunk 444 | Section 61 (Adivansavatarana Parva) | `section_062.html` para 5 | not cited
   - starts: "ti. And Vibhatsu (Arjuna) there obtained for a wife the lotus-eyed and sweet-speeched younger sister of Vasudeva, Subhadra by name. And she became united, in gladness, with Arjuna, the son o..."

**Verdict:** EXPECTED MULTI-HOP FAILURE, honest refusal. The model correctly says the passages cover Krishna and Arjuna but never mention Yayati.

**Notes:** No single chunk holds the chain Krishna, Yadu, Yayati, Puru, Arjuna. Needs query decomposition (Phase 3), agentic retrieval (Phase 5), or a lineage graph (Phase 5/7).

---

## Q6. Who killed Karna in the Kurukshetra war?
_Run on 2026-10-13_

**Answer given:**

> Arjuna slew Karna in single combat [3].

Tokens: prompt 1566, output 10. Citations in answer: [3]

**Top-5 chunks retrieved:**

1. score 0.710 | chunk 1190 | Section 157, 158 (Hidimva-vadha Parva) | `section_158.html` para 4 | not cited
   - starts: "created (by lending a portion of himself) the mighty car-warrior Ghatotkacha as a fit antagonist of Karna of unrivalled energy, in consequence of the dart he had given unto Karna (and which ..."
2. score 0.703 | chunk 1060 | Section 139 (Sambhava Parva) | `section_140.html` para 1 | not cited
   - starts: "at the hands of Partha. As befits thy race take thou anon the whip. And, O worst of mortals, surely thou art not worthy to sway the kingdom of Anga, even as a dog doth not deserve the butter..."
3. score 0.702 | chunk 113 | Section 2 () | `section_003.html` para 15 | **CITED**
   - starts: "ledge after much meditation, is eight thousand, nine hundred and nine. "Then comes the most wonderful Parva called Karna . In this is narrated the appointment of the wise king of Madra as (K..."
4. score 0.699 | chunk 1391 | Section 192 (Swayamvara Parva) | `section_193.html` para 1 | not cited
   - starts: "t. Fighting with each other thus for a few seconds, Bhima the foremost of the Kuru heroes taking up Salya on his arms hurled him to a distance. And Bhimasena, that bull amongst men, surprise..."
5. score 0.694 | chunk 112 | Section 2 () | `section_003.html` para 15 | not cited
   - starts: "n of the remnant of the Sansaptakas. In the Drona Parva, is the death of Alambusha, of Srutayus, of Jalasandha, of Shomadatta, of Virata, of the great warrior-in-chariot Drupada, of Ghatotka..."

**Verdict:** GROUNDED CORRECT ANSWER. Passage [3] (Section II, the contents summary of the whole epic) says 'Then Arjuna slew the great Karna in single combat.'

**Notes:** Adi Parva does not narrate the war, but its Parva-sangraha summarises later parvas. The system used only the passage, not outside knowledge. Results 3 and 5 are neighbouring overlapping chunks of the same passage (near-duplicates).

---

## Q7. Why did Bhishma take a vow of celibacy?
_Run on 2026-10-13_

**Answer given:**

> Bhishma took a vow of celibacy to serve his father, Santanu, and to settle the matter of his children [2]. He pledged to renounce the three worlds and the empire of heaven rather than renounce the truth of this vow [5].

Tokens: prompt 1529, output 51. Citations in answer: [2, 5]

**Top-5 chunks retrieved:**

1. score 0.762 | chunk 814 | Section 102 (Sambhava Parva) | `section_103.html` para 3 | not cited
   - starts: " also I would have chosen him as my lord. Thou art conversant with all the dictates of virtue, knowing all this, do as thou likest.' Thus addressed by that maiden in the presence of the Brah..."
2. score 0.740 | chunk 799 | Section 100 (Sambhava Parva) | `section_101.html` para 9 | **CITED**
   - starts: "quished my right to the throne, I shall now settle the matter of my children. O fisherman, from this day I adopt the vow of Brahmacharya (study and meditation in celibacy). If I die sonless,..."
3. score 0.736 | chunk 619 | Section 76 (Sambhava Parva) | `section_077.html` para 4 | not cited
   - starts: "ow he had spoken of. And, O Bharata, accepting the vow of which he had spoken, at the proper time, Kacha began to conciliate regardfully both his preceptor and (his daughter) Devayani. Indee..."
4. score 0.728 | chunk 804 | Section 102 (Sambhava Parva) | `section_103.html` para 0 | not cited
   - starts: "at vanquisher of all foes, at the command of his mother, went to the city of Varanasi in a single chariot. There Bhishma, the son of Santanu, saw that innumerable monarchs had come from all ..."
5. score 0.716 | chunk 818 | Section 103 (Sambhava Parva) | `section_104.html` para 0 | **CITED**
   - starts: "the ruler of Kasi, possessing beauty and youth, have become desirous of children. Therefore, O thou of mighty arms, at my command, raise offspring on them for the perpetuation of our line. I..."

**Verdict:** SUPPORTED BUT INCOMPLETE. Both citations are real: [2] is the vow passage (Section 100) and [5] contains the pledge 'I would renounce three worlds... but truth I would never renounce'. But [5] is a later conversation with Satyavati, so the second sentence does not explain why he took the vow. The main reason (so that Satyavati's sons would inherit) is only implied.

**Notes:** First live run of the pipeline. The passage with the actual vow ranked second, behind a Section 102 passage about Amba. Generation can only be as good as what retrieval supplies and in what order.

---

## Q8. Who won the 1990 cricket world cup?
_Run on 2026-10-13_

**Answer given:**

> The provided passages do not answer this question. The passages cover events related to the Kuru dynasty, the Pandavas, and the upbringing of princes by Bhishma and Drona.

Tokens: prompt 1509, output 36. Citations in answer: none

**Top-5 chunks retrieved:**

1. score 0.510 | chunk 812 | Section 102 (Sambhava Parva) | `section_103.html` para 2 | not cited
   - starts: "is defeat, returned to his kingdom and continued to rule it virtuously. And O conqueror of hostile towns, the other kings also, who had come to witness, the self-choice ceremony returned to ..."
2. score 0.502 | chunk 1193 | Section 158 (Hidimva-vadha Parva) | `section_159.html` para 2 | not cited
   - starts: " whole world, will rule over all the other monarchs of the earth. There is little doubt that, having by means of Bhima's and Arjuna's prowess conquered the whole earth with her belt of seas,..."
3. score 0.501 | chunk 857 | Section 109 (Sambhava Parva) | `section_110.html` para 0 | not cited
   - starts: "re filled with hope, upon seeing the youthful acts of their illustrious princes. And, O king, in the house of the Kuru chiefs as also of the principal citizens, 'give', 'eat' were the only w..."
4. score 0.496 | chunk 877 | Section 113 (Sambhava Parva) | `section_114.html` para 1 | not cited
   - starts: "d all kings of the world, thus vanquished by him, regarded him as the one single hero on earth even as the celestials regard Indra in heaven. And the kings of earth with joined palms bowed t..."
5. score 0.494 | chunk 1008 | Section 133 (Sambhava Parva) | `section_134.html` para 1 | not cited
   - starts: "to a well. And thereupon the princes strove their best to recover it from the well. But all the efforts the princes made to recover it proved futile. They then began to eye one another bashf..."

**Verdict:** CORRECT REFUSAL. The question is not in the book at all; the model said the passages do not answer it, with one sentence on what they cover.

**Notes:** Tests the refusal rule from the other side: Q6 shows it answers from passages when they contain the answer; this shows it declines when nothing fits.

---
