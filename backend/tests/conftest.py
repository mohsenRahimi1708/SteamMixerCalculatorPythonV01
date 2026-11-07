"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("PST_DB_PATH", str(Path(tempfile.mkdtemp()) / "test.db"))
os.environ.setdefault("PST_RATE_LIMIT_PER_MINUTE", "100000")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI test client with the production lifespan (SQLite baseline included)."""
    with TestClient(create_app()) as test_client:
        yield test_client
