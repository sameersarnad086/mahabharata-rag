"""Chunking: clean paragraphs -> overlapping fixed-size character chunks with metadata.

Baseline (experiment #1): pure fixed-size. The whole corpus is joined into ONE string and
cut every CHUNK_SIZE characters with CHUNK_OVERLAP overlap, ignoring paragraph and section
boundaries on purpose. Structure-aware chunking is a later experiment that must beat this.

Plumbing (loading, offset bookkeeping, metadata) is done. The core is yours:
`fixed_size_spans` below.
"""
import json
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

import config

PARA_SEPARATOR = "\n\n"  # joins paragraphs in the big string; counts toward offsets


@dataclass
class Chunk:
    chunk_id: int
    text: str
    start_char: int            # offsets into the joined corpus string
    end_char: int
    source: str                # e.g. "Mahabharata (Ganguli)"
    parva: str                 # "Adi Parva"
    sections: list[str]        # every section heading this chunk touches, e.g. ["SECTION II", "SECTION III"]
    sub_parvas: list[str]      # every sub-parva it touches (None values dropped)
    first_file: str            # file of the first paragraph touched, for citations
    first_para_index: int      # index of the first paragraph touched within that file


def fixed_size_spans(text: str, size: int, overlap: int) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of each chunk of `text`.

    TODO(me): implement the sliding window.
    Hints:
      - Each chunk starts `size - overlap` characters after the previous one (the "step").
      - The last chunk ends at len(text); don't emit a tiny tail that is ENTIRELY inside
        the previous chunk (think: when does the last window add no new text?).
      - Guard bad configs: overlap >= size would loop forever. Raise ValueError.
      - Empty text -> no chunks.
      - Return offsets, not strings; the caller slices and attaches metadata.
    Run `python tests/test_chunking.py` to check your edge cases.
    """
    raise NotImplementedError("fixed_size_spans is your TODO(me)")


def load_paragraphs(path: Path | None = None) -> list[dict]:
    path = path or config.PROCESSED_DIR / "paragraphs.jsonl"
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def join_corpus(paragraphs: list[dict]) -> tuple[str, list[int]]:
    """Join paragraph texts into one string; return it and each paragraph's start offset."""
    parts, starts, pos = [], [], 0
    for p in paragraphs:
        starts.append(pos)
        parts.append(p["text"])
        pos += len(p["text"]) + len(PARA_SEPARATOR)
    return PARA_SEPARATOR.join(parts), starts


def build_chunks(paragraphs: list[dict], size: int = config.CHUNK_SIZE,
                 overlap: int = config.CHUNK_OVERLAP) -> list[Chunk]:
    corpus, starts = join_corpus(paragraphs)
    chunks = []
    for i, (s, e) in enumerate(fixed_size_spans(corpus, size, overlap)):
        # paragraphs overlapping [s, e): from the one containing s to the one containing e-1
        first = bisect_right(starts, s) - 1
        last = bisect_right(starts, e - 1) - 1
        touched = paragraphs[first:last + 1]
        chunks.append(Chunk(
            chunk_id=i,
            text=corpus[s:e],
            start_char=s,
            end_char=e,
            source=config.SOURCE_NAME,
            parva=config.PARVA,
            sections=list(dict.fromkeys(p["heading"] for p in touched)),
            sub_parvas=list(dict.fromkeys(p["sub_parva"] for p in touched if p["sub_parva"])),
            first_file=touched[0]["file"],
            first_para_index=touched[0]["para_index"],
        ))
    return chunks
