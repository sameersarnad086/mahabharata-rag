"""Embed all chunks with the configured model, cache the vectors, and check for truncation.

Usage: python scripts/run_embedding.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.rag.embedding import embed_chunks, load_model


def main() -> None:
    chunks = [json.loads(l) for l in open(config.PROCESSED_DIR / "chunks.jsonl", encoding="utf-8")]
    model = load_model()
    limit = model.max_seq_length
    print(f"model={config.EMBEDDING_MODEL} dims={model.get_sentence_embedding_dimension()} max_seq_length={limit}")

    # Truncation check: how many chunks are longer than the model can read?
    lengths = [len(model.tokenizer(c["text"], add_special_tokens=True)["input_ids"]) for c in chunks]
    over = sum(n > limit for n in lengths)
    print(f"tokens per chunk: min={min(lengths)} median={sorted(lengths)[len(lengths)//2]} max={max(lengths)}")
    print(f"chunks over the {limit}-token limit (would be silently cut off): {over} of {len(chunks)}")

    vectors = embed_chunks(chunks, model=model)
    print(f"vectors: shape={vectors.shape} dtype={vectors.dtype} "
          f"size={vectors.nbytes / 1e6:.1f} MB; first vector norm={float((vectors[0] ** 2).sum() ** 0.5):.3f}")


if __name__ == "__main__":
    main()
