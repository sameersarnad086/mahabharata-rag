"""Hand-worked checks for the retrieval metrics. Run: python tests/test_metrics.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.metrics import dcg, hit_at_k, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def close(a, b):
    return abs(a - b) < 0.005


def check(name, ok):
    print(("PASS" if ok else "FAIL"), name)
    return ok


r = [
    check("hit@5: a hit at rank 3 -> 1", hit_at_k([False, False, True, False, False], 5) == 1.0),
    check("hit@2: the hit at rank 3 is outside the top 2 -> 0", hit_at_k([False, False, True, False, False], 2) == 0.0),
    check("hit@5: no hit -> 0", hit_at_k([False] * 5, 5) == 0.0),
    check("precision@5: 2 hits of 5 = 0.4", close(precision_at_k([False, True, False, True, False], 5), 0.4)),
    check("recall: 2 of 3 relevant found = 0.67", close(recall_at_k(2, 3), 0.667)),
    check("recall: nothing labelled -> 0, not a crash", recall_at_k(0, 0) == 0.0),
    check("reciprocal rank: rank 1 = 1.0", reciprocal_rank([True, False]) == 1.0),
    check("reciprocal rank: rank 2 = 0.5", reciprocal_rank([False, True]) == 0.5),
    check("reciprocal rank: rank 4 = 0.25", reciprocal_rank([False, False, False, True]) == 0.25),
    check("reciprocal rank: no hit = 0", reciprocal_rank([False, False]) == 0.0),
    check("MRR of 1.0, 0.5, 0 = 0.5 (documented example)",
          close((reciprocal_rank([True]) + reciprocal_rank([False, True]) + reciprocal_rank([False])) / 3, 0.5)),
    check("DCG discounts: rank1 1.00, rank2 0.63, rank3 0.50, rank5 0.39",
          close(dcg([True]), 1.0) and close(dcg([False, True]), 0.631) and close(dcg([False, False, True]), 0.5)
          and close(dcg([False] * 4 + [True]), 0.387)),
    check("nDCG: two hits at ranks 1,2 with 2 relevant = 1.0", close(ndcg_at_k([True, True, False, False, False], 5, 2), 1.0)),
    check("nDCG: two hits at ranks 3,5 with 2 relevant = 0.54 (documented example)",
          close(ndcg_at_k([False, False, True, False, True], 5, 2), 0.544)),
    check("nDCG: one hit at rank 2, one relevant chunk exists = 0.63", close(ndcg_at_k([False, True, False], 5, 1), 0.631)),
    check("nDCG: no hits = 0", ndcg_at_k([False] * 5, 5, 3) == 0.0),
    check("nDCG: zero relevant chunks in corpus -> 0, not a crash", ndcg_at_k([False] * 5, 5, 0) == 0.0),
    check("nDCG never exceeds 1", ndcg_at_k([True] * 5, 5, 20) <= 1.0 + 1e-9),
]
print(f"\n{sum(r)}/{len(r)} passed")
sys.exit(0 if all(r) else 1)
