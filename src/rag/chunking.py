"""Chunking: clean paragraphs -> overlapping fixed-size character chunks with metadata.

Baseline (experiment #1): pure fixed-size. The whole corpus is joined into ONE string and
cut every CHUNK_SIZE characters with CHUNK_OVERLAP overlap, ignoring paragraph and section
boundaries on purpose. Structure-aware chunking is a later experiment that must beat this.

Only the standard library is used (json, bisect, dataclasses, pathlib).
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

    Each chunk starts `size - overlap` characters after the previous one. The last chunk
    stops at len(text). Windows that would add no new text are never emitted: once a chunk
    reaches the end of the text, we stop.
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if overlap < 0 or overlap >= size:
        raise ValueError(f"overlap must satisfy 0 <= overlap < size, got overlap={overlap}, size={size}")

    step = size - overlap
    spans = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        spans.append((start, end))
        if end == len(text):
            break
        start += step
    return spans


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
