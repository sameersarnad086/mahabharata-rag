"""Retrieval: question -> top-k most similar chunks (brute-force cosine similarity).

How it works:
  1. embed the question with the SAME model used for the chunks
  2. score = vectors @ question_vector   (cosine similarity, because every vector has length 1)
  3. pick the k highest scores
  4. look each winner up by row number in the chunks list (row i of the vectors == chunk i)

Only numpy is used for the search itself. At 1,670 vectors this takes about a millisecond.
"""
import json
from dataclasses import dataclass

import numpy as np

import config
from src.rag.embedding import embed_chunks, embed_query, load_model


@dataclass
class Hit:
    rank: int            # 1 = best
    score: float         # cosine similarity (NOT a probability)
    chunk_id: int
    citation: str
    text: str


def top_k_indices(scores: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k highest scores, best first. k larger than the array is clipped."""
    k = max(0, min(k, len(scores)))
    if k == 0:
        return np.array([], dtype=int)
    part = np.sort(np.argpartition(-scores, k - 1)[:k])    # k best; index order makes ties deterministic
    return part[np.argsort(-scores[part], kind="stable")]  # then order just those k, best first


def make_citation(chunk: dict) -> str:
    nums = chunk["section_numbers"]
    if not nums:                                    # the translator's preface has no section number
        where = chunk["sections"][0].title()
    elif len(nums) == 1:
        where = f"Section {nums[0]}"
    else:
        where = f"Sections {nums[0]}-{nums[-1]}"
    sub = f" ({', '.join(chunk['sub_parvas'])})" if chunk["sub_parvas"] else ""
    return f"{chunk['source']}, {chunk['parva']}, {where}{sub} [{chunk['first_file']}, para {chunk['first_para_index']}]"


class Retriever:
    def __init__(self) -> None:
        self.chunks = [json.loads(l) for l in open(config.PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]
        self.model = load_model()
        self.vectors = embed_chunks(self.chunks, model=self.model)   # uses the disk cache
        assert len(self.vectors) == len(self.chunks), "vectors and chunks are out of step"

    def search(self, question: str, k: int = config.TOP_K) -> list[Hit]:
        scores = self.vectors @ embed_query(self.model, question)
        return [
            Hit(rank=r, score=float(scores[i]), chunk_id=int(i),
                citation=make_citation(self.chunks[i]), text=self.chunks[i]["text"])
            for r, i in enumerate(top_k_indices(scores, k), start=1)
        ]
