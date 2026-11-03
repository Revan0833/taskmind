import os
from pathlib import Path
from datetime import datetime, timedelta

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
DATABASE_PATH = BASE_DIR / "tasks.sqlite3"

# ChromaDB & Embedding Configuration
CHROMA_COLLECTION_NAME = "workshop_project_notes"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Reference Workshop Date: Default to 7 days from now (or custom date)
# This allows relative date resolution like "3 days before workshop" or "AV check 48h prior"
NOW = datetime.now()
TARGET_WORKSHOP_DATE = NOW + timedelta(days=7)
TARGET_WORKSHOP_DATE_STR = TARGET_WORKSHOP_DATE.strftime("%Y-%m-%d")

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
