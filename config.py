"""Single place for every tunable. Experiments change values HERE, never inline."""
from pathlib import Path

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw" / "mahabharata" / "adi_parva"
PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache"

# --- Source (Phase 0) ---
SOURCE_NAME = "Mahabharata (Ganguli)"
PARVA = "Adi Parva"
SECTION_URL = "https://sacred-texts.com/hin/m01/m01{n:03d}.htm"
# Page m01001 is the Translator's Preface; page m01002 is Section I (so page = section + 1).
# Adi Parva should have 236 sections -> pages 001..237. Verify after download.
NUM_SECTIONS = 240  # upper bound; downloader stops at the first 404

# --- Phase 1 knobs (filled in when we get there) ---
CHUNK_SIZE = 1000      # characters
CHUNK_OVERLAP = 200
TOP_K = 5
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # chosen with user; 384 dims, ~512-token limit (verify on model card)
EMBEDDING_BATCH_SIZE = 32
# bge models are trained to see this prefix on QUERIES (not on chunks) for retrieval. A later experiment.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
USE_QUERY_PREFIX = False  # baseline: off. Test on/off as its own one-variable experiment.
# Generator: Gemini via the google-genai library. Key is read from the GEMINI_API_KEY environment variable.
# The model id below is UNVERIFIED: run `python scripts/list_models.py` once the key is set and copy the exact id.
LLM_MODEL = "gemini-3.1-flash-lite"
LLM_TEMPERATURE = 0.0       # 0 = as repeatable as possible, which is what we want for evaluation
LLM_MAX_OUTPUT_TOKENS = 1024
