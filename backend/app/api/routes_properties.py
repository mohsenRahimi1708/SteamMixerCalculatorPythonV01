"""IF97 property lookup."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import PropertiesResponse
from app.thermo import if97

router = APIRouter(tags=["properties"])


@router.get("/api/properties", response_model=PropertiesResponse, summary="IF97 state point")
def properties(
    P_bar: float = Query(..., ge=1, le=300, description="pressure [bar]"),
    T_C: float = Query(..., ge=-20, le=700, description="temperature [\u00b0C]"),
) -> dict:
    """Density, enthalpy, entropy, cp, viscosity and conductivity at (P, T)."""
    return if97.props_pt(P_bar, T_C)
