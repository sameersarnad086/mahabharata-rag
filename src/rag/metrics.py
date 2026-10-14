"""Retrieval metrics. Pure functions, no model or data needed.

Inputs are lists of True/False flags, one per returned chunk in rank order (rank 1 first):
True means "this chunk is a hit" (it matches the gold label). All metrics are per question;
averaging over questions is done by the caller.
"""
import math


def hit_at_k(flags: list[bool], k: int) -> float:
    """1.0 if any of the top k chunks is a hit, else 0.0."""
    return 1.0 if any(flags[:k]) else 0.0


def precision_at_k(flags: list[bool], k: int) -> float:
    """Fraction of the top k chunks that are hits."""
    return sum(flags[:k]) / k


def recall_at_k(found: int, total: int) -> float:
    """Fraction of the labelled relevant items (sections or phrases) found in the top k."""
    return found / total if total else 0.0


def reciprocal_rank(flags: list[bool]) -> float:
    """1 / rank of the first hit; 0.0 if there is no hit in the list."""
    for i, f in enumerate(flags, start=1):
        if f:
            return 1.0 / i
    return 0.0


def dcg(flags: list[bool]) -> float:
    """Discounted cumulative gain with binary gains: each hit at rank r earns 1 / log2(r + 1)."""
    return sum(1.0 / math.log2(i + 1) for i, f in enumerate(flags, start=1) if f)


def ndcg_at_k(flags: list[bool], k: int, n_relevant: int) -> float:
    """nDCG@k with binary gains. `n_relevant` is how many relevant chunks exist in the whole corpus,
    so the ideal ordering puts min(k, n_relevant) hits at the top."""
    ideal = dcg([True] * min(k, n_relevant))
    return dcg(flags[:k]) / ideal if ideal > 0 else 0.0
