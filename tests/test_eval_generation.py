"""Checks for the generation-evaluation logic. No network: the judge is replaced by a fake.
Run: python tests/test_eval_generation.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag import eval_generation as E
from src.rag.generation import SYSTEM_PROMPT
from src.rag.judge import Judge, JudgeError


def check(name, ok):
    print(("PASS" if ok else "FAIL"), name)
    return ok


class P:
    def __init__(self, rank, text):
        self.rank, self.text, self.score, self.chunk_id, self.citation = rank, text, 1.0, rank, f"Section {rank}"


def fake_ask(replies):
    """Return an ask() that answers each judge job from a dict keyed by a word in the task text."""
    def ask(system, user):
        for key, reply in replies.items():
            if key in system:
                return {"reply": reply(user) if callable(reply) else reply, "usage": {"prompt": 10, "output": 5, "thinking": 0}}
        raise AssertionError("unexpected judge job")
    return ask


Q = {"id": "R01", "type": "plain", "split": "working", "answerable": "yes", "question": "Who was Sakuntala's mother?",
     "expected_answer": "Menaka", "evidence_phrases": "begat on Menaka a daughter"}
HITS = [P(1, "Other text."), P(2, "The Rishi begat on Menaka a daughter named Sakuntala.")]
ANSWER = "Her mother was Menaka, an Apsara [2]. She was left in the forest [2]."

judge = Judge(fake_ask({
    "Grade whether the answer is correct": {"score": 1, "reason": "ok"},
    "Break the answer": {"claims": ["Mother was Menaka", "Menaka was an Apsara", "She was left in the forest"]},
    "numbered claim": {"verdicts": [{"claim_number": 1, "supported": True}, {"claim_number": 2, "supported": False},
                                    {"claim_number": 3, "supported": True}]},
    "numbered pairs": {"results": [{"pair": 1, "backed": False, "reason": "Apsara"}, {"pair": 2, "backed": True}]},
    "addresses what the question": {"relevant": True, "reason": "yes"},
}))
rec = E.score_answer(Q, HITS, ANSWER, judge, "end-to-end")

results = [
    check("refusal sentence in the generator's system prompt matches ours", E.REFUSAL_SENTENCE in SYSTEM_PROMPT),
    check("refusal detected, with an added sentence", E.is_refusal(E.REFUSAL_SENTENCE + " They cover Menaka.")),
    check("normal answer is not a refusal", not E.is_refusal(ANSWER)),
    check("cited sentences split with their numbers",
          E.split_cited_sentences("A [2]. B [1][3]. C has none.") == [("A [2].", [2]), ("B [1][3].", [1, 3])]),
    check("newline also ends a sentence", len(E.split_cited_sentences("A [1]\nB [2]")) == 2),
    check("gold found when phrase is in a passage", E.gold_found(HITS, ["begat on menaka a daughter"])),
    check("gold not found otherwise", not E.gold_found(HITS[:1], ["begat on Menaka"])),
    check("answerable + refused + gold missing = retrieval fault",
          E.classify(True, True, "end-to-end", False) == "false_refusal_retrieval"),
    check("answerable + refused + gold present = generation fault",
          E.classify(True, True, "end-to-end", True) == "false_refusal_generation"),
    check("ideal context refusal is always a generation fault",
          E.classify(True, True, "ideal-context", None) == "false_refusal_generation"),
    check("unanswerable: refusal correct, answer wrong",
          E.classify(False, True, "end-to-end", None) == "correct_refusal"
          and E.classify(False, False, "end-to-end", None) == "should_have_refused"),
    check("correctness taken from judge", rec["correctness"] == 1.0),
    check("faithfulness = 2 of 3 claims supported", abs(rec["faithfulness"] - 2 / 3) < 1e-9),
    check("citation support = 1 of 2 sentences backed", rec["citation_support"] == 0.5),
    check("relevance recorded", rec["relevance"] == 1.0),
    check("judge was called 5 times for this answer", judge.calls == 5),
]

# refusal to an answerable question: scored 0 by code, judge not called
j2 = Judge(fake_ask({}))
r2 = E.score_answer(Q, HITS, E.REFUSAL_SENTENCE, j2, "end-to-end")
results += [check("answerable refusal: correctness 0, no judge calls", r2["correctness"] == 0.0 and j2.calls == 0),
            check("answerable refusal outcome", r2["outcome"] == "false_refusal_generation")]

# unanswerable question that was answered: faithfulness/citations run, correctness and relevance do not
Qu = dict(Q, id="G01", answerable="no", expected_answer="", evidence_phrases="")
j3 = Judge(fake_ask({"Break the answer": {"claims": ["x"]}, "numbered claim": {"verdicts": [{"claim_number": 1, "supported": False}]},
                     "numbered pairs": {"results": [{"pair": 1, "backed": False}, {"pair": 2, "backed": False}]}}))
r3 = E.score_answer(Qu, HITS, ANSWER, j3, "end-to-end")
results += [check("unanswerable but answered flagged", r3["outcome"] == "should_have_refused" and r3["correctness"] is None),
            check("unanswerable answered: faithfulness still scored", r3["faithfulness"] == 0.0)]

# citation to a passage that does not exist counts as unbacked without asking the judge
j4 = Judge(fake_ask({"Break the answer": {"claims": ["x"]}, "numbered claim": {"verdicts": [{"claim_number": 1, "supported": True}]},
                     "numbered pairs": {"results": [{"pair": 1, "backed": True}]}}))
r4 = E.score_answer(dict(Q, answerable="no"), HITS, "Fact one [2]. Fact two [9].", j4, "end-to-end")
results.append(check("made-up citation number counts as unbacked", r4["citation_support"] == 0.5 and r4["invalid_citations"] == [9]))

# bad judge replies are rejected
bad = Judge(fake_ask({"Grade whether the answer is correct": {"score": 0.7}}))
try:
    bad.correctness("q", "e", "a")
    results.append(check("out-of-range correctness score rejected", False))
except JudgeError:
    results.append(check("out-of-range correctness score rejected", True))
short = Judge(fake_ask({"numbered claim": {"verdicts": [{"claim_number": 1, "supported": True}]}}))
try:
    short.verify_claims(HITS, ["a", "b"])
    results.append(check("missing verdict rejected", False))
except JudgeError:
    results.append(check("missing verdict rejected", True))

# ideal-context passages
chunks = [{"text": "Alpha begat Beta.", "section_numbers": [1], "sections": ["S"], "sub_parvas": [], "source": "M", "parva": "P",
           "first_file": "f", "first_para_index": 0},
          {"text": "Alpha begat Beta. Gamma ruled.", "section_numbers": [2], "sections": ["S"], "sub_parvas": [], "source": "M",
           "parva": "P", "first_file": "f", "first_para_index": 0},
          {"text": "Nothing here.", "section_numbers": [3], "sections": ["S"], "sub_parvas": [], "source": "M", "parva": "P",
           "first_file": "f", "first_para_index": 0}]
ideal = E.pick_ideal_passages(chunks, ["Alpha begat Beta", "Gamma ruled"], 5)
results += [check("ideal context picks only chunks holding evidence", [p.chunk_id for p in ideal] == [0, 1]),
            check("ideal context respects the cap", len(E.pick_ideal_passages(chunks, ["Alpha begat Beta"], 1)) == 1)]

# summary
s = E.summarise([rec, r2, r3])
results += [check("summary counts answerable and unanswerable", s["n_answerable"] == 2 and s["n_unanswerable"] == 1),
            check("summary correctness includes the refusal as 0", abs(s["correctness"] - 0.5) < 1e-9),
            check("summary refusal table", s["refusal"] == {"correct_refusals": 0, "unanswerable": 1, "false_refusals": 1, "answerable": 2})]
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
