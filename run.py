#!/usr/bin/env python3
"""
TaskMind AI - Runner script
Launches the FastAPI server serving both the REST API and the Frontend SPA.
"""

import sys
import os

# Set standard output to UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import uvicorn
from backend.config import HOST, PORT

if __name__ == "__main__":
    print("=" * 70)
    print(f"[*] Starting TaskMind AI - Workshop Task Management Agent")
    print(f"[*] Web Application available at: http://{HOST}:{PORT}")
    print(f"[*] Interactive API docs at: http://{HOST}:{PORT}/docs")
    print(f"[*] Vector Store: ChromaDB with all-MiniLM-L6-v2 embeddings")
    print("=" * 70)
    uvicorn.run("backend.server:app", host=HOST, port=PORT, reload=False)
