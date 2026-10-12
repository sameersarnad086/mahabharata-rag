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
EMBEDDING_MODEL = None  # decided together in Phase 1
LLM_MODEL = None
