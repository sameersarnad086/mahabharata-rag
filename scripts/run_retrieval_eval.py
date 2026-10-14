"""Score the retriever on the labelled retrieval questions.

Default: the WORKING set only, with per-question detail (this is the set we study and tune on).
The HELD-OUT set is for milestones only: it needs --confirm-milestone "reason", prints aggregate
numbers only (no per-question or per-type lines), and every run is appended to eval/heldout_runs.log.

Usage:
  python scripts/run_retrieval_eval.py                        # working set
  python scripts/run_retrieval_eval.py --exclude-summaries    # ignore Sections 1, 2, 95 as gold
  python scripts/run_retrieval_eval.py --split held-out --confirm-milestone "baseline"
  python scripts/run_retrieval_eval.py --save baseline_working
"""
import argparse
import collections
import datetime
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.eval_retrieval import CHECKS, KS, evaluate, load_questions, mean, summarise
from src.rag.retrieval import Retriever


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT, text=True).strip()
    except Exception:
        return "unknown"


def headline(results, label):
    print(f"\n{label}   (n = {len(results)} questions)")
    print(f"{'check':8s} {'hit@5':>10s} {'prec@5':>8s} {'recall@5':>9s} {'MRR@5':>7s} {'nDCG@5':>8s}")
    for c in CHECKS:
        h = int(sum(r.scores[c]["hit@5"] for r in results))
        print(f"{c:8s} {h:3d}/{len(results):<3d}={mean(results,c,'hit@5'):4.2f} {mean(results,c,'precision@5'):8.2f}"
              f" {mean(results,c,'recall@5'):9.2f} {mean(results,c,'mrr@5'):7.2f} {mean(results,c,'ndcg@5'):8.2f}")


def by_k(results):
    print(f"\n{'':8s}" + "".join(f"  hit@{k:<3d}" for k in KS) + "".join(f"  MRR@{k:<3d}" for k in KS))
    for c in CHECKS:
        print(f"{c:8s}" + "".join(f"  {mean(results,c,f'hit@{k}'):6.2f}" for k in KS)
              + "".join(f"  {mean(results,c,f'mrr@{k}'):7.2f}" for k in KS))


def by_type(results):
    print(f"\n{'type':11s} {'n':>3s}  {'hit@5 section':>13s} {'hit@5 phrase':>13s} {'MRR@5 phrase':>13s}")
    groups = collections.OrderedDict()
    for r in results:
        groups.setdefault(r.type, []).append(r)
    for t, rs in groups.items():
        print(f"{t:11s} {len(rs):3d}  {mean(rs,'section','hit@5'):13.2f} {mean(rs,'phrase','hit@5'):13.2f} {mean(rs,'phrase','mrr@5'):13.2f}")


def per_question(results):
    print(f"\n{'id':4s} {'type':10s} {'band':6s} {'sec':>4s} {'phr':>4s}  question   (rank of first hit in the top 10, '-' = none)")
    for r in results:
        f = lambda c: str(r.first_rank[c]) if r.first_rank[c] else "-"
        print(f"{r.id:4s} {r.type:10s} {r.band:6s} {f('section'):>4s} {f('phrase'):>4s}  {r.question[:70]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["working", "held-out", "all"], default="working")
    ap.add_argument("--exclude-summaries", action="store_true")
    ap.add_argument("--confirm-milestone", metavar="REASON")
    ap.add_argument("--save", metavar="NAME")
    args = ap.parse_args()

    touches_held_out = args.split in ("held-out", "all")
    if touches_held_out and not args.confirm_milestone:
        sys.exit("Refusing: the held-out set is for milestones only. Re-run with --confirm-milestone \"reason\" "
                 "(for example: baseline, end of Phase 3 chunking).")

    qs = load_questions()
    if args.split != "all":
        qs = [q for q in qs if q["split"] == args.split]
    results, dropped = evaluate(Retriever(), qs, exclude_summaries=args.exclude_summaries)

    cfg = {"chunk_size": config.CHUNK_SIZE, "chunk_overlap": config.CHUNK_OVERLAP, "embedding_model": config.EMBEDDING_MODEL,
           "query_prefix": config.USE_QUERY_PREFIX, "k_retrieved": max(KS), "exclude_summaries": args.exclude_summaries,
           "commit": git_commit(), "date": str(datetime.date.today())}
    label = f"{args.split.upper()} set" + (" (summary sections excluded)" if args.exclude_summaries else "")
    print("config:", json.dumps(cfg))
    if dropped:
        print(f"left out of this variant (no non-summary gold): {len(dropped)} questions")
    headline(results, label)
    by_k(results)

    if touches_held_out:
        print("\n(held-out run: aggregates only, no per-question or per-type detail by design)")
        log = config.ROOT / "eval" / "heldout_runs.log"
        s = summarise(results)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"reason": args.confirm_milestone, "split": args.split, "config": cfg,
                                "n": s["n"], "section": {k: round(v, 3) for k, v in s["section"].items() if k.endswith("@5")},
                                "phrase": {k: round(v, 3) for k, v in s["phrase"].items() if k.endswith("@5")}}) + "\n")
        print(f"logged to {log.relative_to(config.ROOT)}")
    else:
        by_type(results)
        per_question(results)

    if args.save:
        out = config.ROOT / "eval" / "results"
        out.mkdir(exist_ok=True)
        payload = {"config": cfg, "split": args.split, "summary": summarise(results)}
        if not touches_held_out:
            payload["questions"] = [{"id": r.id, "type": r.type, "first_rank": r.first_rank, "scores": r.scores,
                                     "top_sections": r.top_sections} for r in results]
        (out / f"{args.save}.json").write_text(json.dumps(payload, indent=2))
        print(f"saved eval/results/{args.save}.json")


if __name__ == "__main__":
    main()
