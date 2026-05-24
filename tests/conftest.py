"""Shared fixtures for backend tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def client_with_tmp_db(tmp_db_path, monkeypatch):
    """FastAPI TestClient pointing at an isolated SQLite DB."""
    from fastapi.testclient import TestClient

    from backend import main as backend_main
    monkeypatch.setattr(backend_main, "DB_PATH", tmp_db_path)
    with TestClient(backend_main.app) as c:
        yield c
