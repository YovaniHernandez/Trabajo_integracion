import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CATEGORIES_DIR = CONFIG_DIR / "categories"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
RESEARCH_DIR = DATA_DIR / "research"

# Ensure runtime directories exist
for directory in [INPUT_DIR, OUTPUT_DIR, RESEARCH_DIR, CATEGORIES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Load .env (check local first, then parent project directory)
load_dotenv(PROJECT_ROOT / ".env")
if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    load_dotenv(PROJECT_ROOT.parent / "Proyecto" / ".env")

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or ""

# LLM Models
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

# Processing Defaults
DEFAULT_START_ROW = 5
MAX_SEARCH_RESULTS = 4
REQUEST_TIMEOUT_SECONDS = 15
PAUSE_BETWEEN_ROWS = 0.5  # seconds
