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
NUM_SECTIONS = 236  # Adi Parva has 236 sections in Ganguli's numbering; verify after download

# --- Phase 1 knobs (filled in when we get there) ---
CHUNK_SIZE = 1000      # characters
CHUNK_OVERLAP = 200
TOP_K = 5
EMBEDDING_MODEL = None  # decided together in Phase 1
LLM_MODEL = None
