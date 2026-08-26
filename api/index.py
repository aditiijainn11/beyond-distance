import sys
from pathlib import Path

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.database import init_db, SessionLocal
from app.seed_data import seed_database
from app.main import app

# Initialize DB on cold start
try:
    init_db()
    db = SessionLocal()
    seed_database(db)
    db.close()
except Exception as e:
    print(f"Warning during cold-start DB init: {e}")
