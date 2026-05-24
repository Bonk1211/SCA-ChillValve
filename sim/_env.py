"""Load .env from repo root into os.environ on import.

Used by entry points (backend, CLI engine, scripts) so all of them see the
same configuration. No-op if .env doesn't exist or python-dotenv is missing.
Safe to import multiple times.
"""
from __future__ import annotations

from pathlib import Path

_loaded = False


def load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


load()
