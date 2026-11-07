"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.db.models import RunStore


def get_store(request: Request) -> RunStore:
    """Run store attached to the application state during startup."""
    return request.app.state.store
