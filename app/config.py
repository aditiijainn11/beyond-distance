import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel serverless functions have a read-only filesystem except /tmp
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    DATA_DIR = Path("/tmp")
else:
    DATA_DIR = BASE_DIR / "data"
    try:
        DATA_DIR.mkdir(exist_ok=True, parents=True)
    except Exception:
        DATA_DIR = Path("/tmp")

DB_PATH = DATA_DIR / "beyond_distance.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Default LLM configurations
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
