import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "beyond_distance.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Default LLM configurations
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # "gemini", "openai", "groq", "mock"
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
