"""Run history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_store
from app.db.models import RunStore
from app.models.schemas import RunCreate, RunDetail, RunSummary

router = APIRouter(tags=["history"])


@router.post("/api/runs", response_model=RunDetail, status_code=201, summary="Save a run")
def save_run(request: RunCreate, store: RunStore = Depends(get_store)) -> dict:
    """Persist a completed simulation for the History screen."""
    record = store.save(
        kind=request.kind,
        label=request.label,
        summary={**request.model_dump(exclude={"kind", "label", "payload"})},
        payload=request.payload,
    )
    return record.detail()


@router.get("/api/runs", response_model=list[RunSummary], summary="List stored runs")
def list_runs(
    limit: int = Query(50, ge=1, le=500), store: RunStore = Depends(get_store)
) -> list[dict]:
    """Most recent runs first."""
    return [record.summary() for record in store.list(limit=limit)]


@router.get("/api/runs/{run_id}", response_model=RunDetail, summary="Read a stored run")
def get_run(run_id: str, store: RunStore = Depends(get_store)) -> dict:
    """Full payload of one run."""
    record = store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return record.detail()


@router.delete("/api/runs/{run_id}", status_code=204, summary="Delete a stored run")
def delete_run(run_id: str, store: RunStore = Depends(get_store)) -> None:
    """Remove one stored run."""
    if not store.delete(run_id):
        raise HTTPException(status_code=404, detail="run_not_found")
