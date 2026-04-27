"""
Run from the project root (500-game/):

    python3 backend/run.py

or equivalently:

    uvicorn backend.api.main:app --reload --port 8000
"""
import sys
import os
import uvicorn

# Ensure the project root (500-game/) is on sys.path so that
# `backend.api.main` resolves correctly with its relative imports.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
