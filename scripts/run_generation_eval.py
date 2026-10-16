"""Score the generator (and judge-graded answer quality) on the labelled questions.

Default: WORKING set, end-to-end AND ideal-context modes, with per-question detail.
The HELD-OUT set is for milestones only: it needs --confirm-milestone "reason", prints aggregates only,
and every run is appended to eval/heldout_runs.log (the same log the retrieval evaluation uses).

Generator answers and judge replies are cached on disk, so re-running an unchanged setup is free and a
crashed run resumes where it stopped. Use --no-cache to force fresh calls.

Usage:
  python scripts/run_generation_eval.py --ids R01,R03 --mode end-to-end     # a small trial
  python scripts/run_generation_eval.py --save baseline_working
  python scripts/run_generation_eval.py --split held-out --confirm-milestone "baseline" --save baseline_heldout
"""
import argparse
import datetime
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag import evalcache
from src.rag import eval_generation as E
from src.rag import generation
from src.rag.generation import build_prompt, generate_answer
from src.rag.judge import Judge, JudgeError, make_google_ask


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT, text=True).strip()
    except Exception:
        return "unknown"


def get_answer(client, question, hits, use_cache):
    """Generator answer text, from cache if the same prompt was already answered."""
    system, user = build_prompt(question, hits)

    def compute():
        a = generate_answer(question, hits, client=client)
        return {"text": a.text, "prompt_tokens": a.prompt_tokens, "output_tokens": a.output_tokens}

    d = evalcache.cached(["answer", config.LLM_MODEL, config.LLM_TEMPERATURE, config.LLM_MAX_OUTPUT_TOKENS, system, user],
                         compute, use_cache)
    return d["text"]


def fmt(v):
    return "  -  " if v is None else f"{v:5.2f}"


def print_summary(label, s):
    print(f"\n{label}   (n = {s['n']}: {s['n_answerable']} answerable, {s['n_unanswerable']} unanswerable"
          + (f", {s['n_errors']} ERRORS left out" if s["n_errors"] else "") + ")")
    print(f"  correctness (refusals count 0)   {fmt(s['correctness'])}")
    print(f"  correctness (when it answered)   {fmt(s['correctness_when_answered'])}")
    print(f"  faithfulness                     {fmt(s['faithfulness'])}")
    print(f"  citation support                 {fmt(s['citation_support'])}")
    print(f"  relevance                        {fmt(s['relevance'])}")
    if s["gold_found_rate"] is not None:
        print(f"  gold text was in the passages    {fmt(s['gold_found_rate'])}")
    r = s["refusal"]
    print(f"  refusals: correct {r['correct_refusals']}/{r['unanswerable']} of the unanswerable;"
          f" false {r['false_refusals']}/{r['answerable']} of the answerable")
    print(f"  outcomes: {s['outcomes']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["end-to-end", "ideal-context", "both"], default="both")
    ap.add_argument("--split", choices=["working", "held-out", "all"], default="working")
    ap.add_argument("--confirm-milestone", metavar="REASON")
    ap.add_argument("--ids", help="comma-separated question ids, for a small trial")
    ap.add_argument("--limit", type=int, help="only the first N questions")
    ap.add_argument("--save", metavar="NAME")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    touches_held_out = args.split in ("held-out", "all")
    if touches_held_out and not args.confirm_milestone:
        sys.exit("Refusing: the held-out set is for milestones only. Re-run with --confirm-milestone \"reason\" "
                 "(for example: baseline, end of Phase 3 chunking).")

    generation.RETRY_WAITS = config.EVAL_RETRY_WAITS     # evaluation runs are long, so wait longer on 503/429
    qs = E.load_questions()
    if args.split != "all":
        qs = [q for q in qs if q["split"] == args.split]
    if args.ids:
        wanted = set(args.ids.split(","))
        qs = [q for q in qs if q["id"] in wanted]
    if args.limit:
        qs = qs[:args.limit]
    if not qs:
        sys.exit("No questions selected.")

    modes = ["end-to-end", "ideal-context"] if args.mode == "both" else [args.mode]
    use_cache = not args.no_cache

    from google import genai
    client = genai.Client()
    judge = Judge(make_google_ask(use_cache))
    if "end-to-end" in modes:
        from src.rag.retrieval import Retriever
        retriever = Retriever()
        chunks = retriever.chunks
    else:
        chunks = [json.loads(l) for l in open(config.PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]

    cfg = {"generator": config.LLM_MODEL, "judge": config.JUDGE_MODEL, "k": config.TOP_K, "chunk_size": config.CHUNK_SIZE,
           "chunk_overlap": config.CHUNK_OVERLAP, "embedding_model": config.EMBEDDING_MODEL,
           "split": args.split, "commit": git_commit(), "date": str(datetime.date.today())}
    print("config:", json.dumps(cfg))

    all_records = {}
    for mode in modes:
        records, bad_streak = [], 0
        print(f"\n--- {mode}: {len(qs)} questions ---")
        for q in qs:
            try:
                if mode == "end-to-end":
                    hits = retriever.search(q["question"], config.TOP_K)
                elif q["answerable"] == "yes":
                    hits = E.pick_ideal_passages(chunks, E.split_phrases(q["evidence_phrases"]), config.TOP_K)
                else:
                    continue                         # no gold text exists for an unanswerable question
                text = get_answer(client, q["question"], hits, use_cache)
                if not text:
                    raise JudgeError("generator returned empty text")
                rec = E.score_answer(q, hits, text, judge, mode)
                bad_streak = 0
            except Exception as e:                   # one failing question must not lose the whole run
                rec = {"id": q["id"], "type": q["type"], "split": q["split"], "mode": mode,
                       "answerable": q["answerable"] == "yes", "question": q["question"], "error": f"{type(e).__name__}: {e}"}
                bad_streak += 1
                if bad_streak >= 3:
                    sys.exit(f"Stopping: 3 failures in a row. Last: {rec['error']}")
            records.append(rec)
            if not touches_held_out:
                if "error" in rec:
                    print(f"{rec['id']:4s} ERROR {rec['error'][:90]}")
                else:
                    print(f"{rec['id']:4s} {rec['type']:10s} {rec['outcome']:25s} corr={fmt(rec['correctness'])} "
                          f"faith={fmt(rec['faithfulness'])} cite={fmt(rec['citation_support'])} rel={fmt(rec['relevance'])}")
        all_records[mode] = records

    summaries = {m: E.summarise(r) for m, r in all_records.items()}
    for m in modes:
        print_summary(f"{args.split.upper()} set, {m}", summaries[m])
        if not touches_held_out:
            print("  by question type:")
            for t, v in E.by_type(all_records[m]).items():
                print(f"    {t:10s} n={v['n']:2d} correctness={fmt(v['correctness'])} faithfulness={fmt(v['faithfulness'])}"
                      f" refused={v['refused']}")

    u = judge.usage
    price_in, price_out = config.JUDGE_PRICE_PER_M_TOKENS
    cost = (u["prompt"] * price_in + (u["output"] + u["thinking"]) * price_out) / 1e6
    print(f"\njudge calls this run (cache hits excluded from cost): {judge.calls}; tokens in {u['prompt']}, "
          f"out {u['output']}, thinking {u['thinking']}; about ${cost:.3f} at the listed prices")

    if touches_held_out:
        print("\n(held-out run: aggregates only, no per-question detail by design)")
        log = config.ROOT / "eval" / "heldout_runs.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "generation", "reason": args.confirm_milestone, "config": cfg,
                                "summaries": summaries}, default=float) + "\n")
        print(f"logged to {log.relative_to(config.ROOT)}")

    if args.save:
        out = config.ROOT / "eval" / "results"
        out.mkdir(exist_ok=True)
        payload = {"config": cfg, "summaries": summaries}
        if not touches_held_out:
            payload["records"] = all_records
        (out / f"gen_{args.save}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"saved eval/results/gen_{args.save}.json")


if __name__ == "__main__":
    main()
