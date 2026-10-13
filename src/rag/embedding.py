"""Embeddings: chunk text -> one fixed-length vector per chunk, cached on disk.

Library: sentence-transformers (wraps PyTorch + Hugging Face models). Model set in config.py.
Vectors are L2-normalised (length 1), so cosine similarity == plain dot product. That is what
the numpy search in the next step relies on.

Cache: vectors are saved to data/cache/ under a name that includes a fingerprint of the model
name and every chunk's text. Change the model, the chunk size or the cleaning -> new fingerprint
-> re-embed. Nothing stale can be reused by accident.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

import config


def load_model(name: str = config.EMBEDDING_MODEL):
    from sentence_transformers import SentenceTransformer  # heavy import, load lazily
    return SentenceTransformer(name)


def fingerprint(model_name: str, texts: list[str]) -> str:
    h = hashlib.sha256(model_name.encode("utf-8"))
    for t in texts:
        h.update(b"\x00")
        h.update(t.encode("utf-8"))
    return h.hexdigest()[:16]


def cache_path(model_name: str, texts: list[str]) -> Path:
    slug = model_name.replace("/", "__")
    return config.CACHE_DIR / f"emb_{slug}_{fingerprint(model_name, texts)}.npy"


def embed_texts(model, texts: list[str], batch_size: int = config.EMBEDDING_BATCH_SIZE) -> np.ndarray:
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,   # unit-length vectors
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)


def embed_chunks(chunks: list[dict], model=None, model_name: str = config.EMBEDDING_MODEL) -> np.ndarray:
    """Return an array of shape (n_chunks, dims). Uses the disk cache when it can."""
    texts = [c["text"] for c in chunks]
    path = cache_path(model_name, texts)
    if path.exists():
        vectors = np.load(path)
        print(f"cache hit: {path.name} {vectors.shape}")
        return vectors
    model = model or load_model(model_name)
    vectors = embed_texts(model, texts)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(path, vectors)
    path.with_suffix(".json").write_text(json.dumps(
        {"model": model_name, "n_chunks": len(texts), "dims": int(vectors.shape[1]),
         "chunk_size": config.CHUNK_SIZE, "chunk_overlap": config.CHUNK_OVERLAP}, indent=2))
    print(f"embedded and cached: {path.name} {vectors.shape}")
    return vectors


def embed_query(model, question: str) -> np.ndarray:
    text = (config.QUERY_PREFIX + question) if config.USE_QUERY_PREFIX else question
    return embed_texts(model, [text])[0]
