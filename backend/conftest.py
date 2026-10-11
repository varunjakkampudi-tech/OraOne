"""Load .env for pytest before any `app.*` modules are imported.

`app.core.config` raises at import time if `JWT_SECRET_KEY` isn't set (or is
too short). We want pytest to find it in `backend/.env` just like uvicorn
does at server start.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
