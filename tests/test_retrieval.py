"""Checks for the ranking function (pure numpy, no model needed). Run: python tests/test_retrieval.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.retrieval import top_k_indices


def check(name, got, want):
    ok = list(got) == list(want)
    print(("PASS" if ok else "FAIL"), name, "" if ok else f"\n   got  {list(got)}\n   want {list(want)}")
    return ok


s = np.array([0.1, 0.9, 0.5, 0.7, 0.3])
results = [
    check("top 3, best first", top_k_indices(s, 3), [1, 3, 2]),
    check("top 1", top_k_indices(s, 1), [1]),
    check("k larger than the array is clipped", top_k_indices(s, 99), [1, 3, 2, 4, 0]),
    check("k = 0 gives nothing", top_k_indices(s, 0), []),
    check("empty scores", top_k_indices(np.array([]), 3), []),
    check("ties keep a stable order", top_k_indices(np.array([0.5, 0.5, 0.5]), 3), [0, 1, 2]),
]
# the dot product of unit vectors equals cosine similarity
rng = np.random.default_rng(0)
a, b = rng.normal(size=8), rng.normal(size=8)
cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
au, bu = a / np.linalg.norm(a), b / np.linalg.norm(b)
results.append(abs(float(au @ bu) - float(cos)) < 1e-9)
print(("PASS" if results[-1] else "FAIL"), "dot product of unit vectors == cosine similarity")
print(f"\n{sum(results)}/{len(results)} passed")
