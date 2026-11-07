"""Heat transfer coefficient diagnostics."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import HtcMethod, HtcResponse
from app.thermo import htc as htc_mod
from app.thermo.geometry import DEFAULT_GEOMETRY

router = APIRouter(tags=["htc"])


@router.get("/api/htc", response_model=HtcResponse, summary="Tube-side heat transfer coefficient")
def htc(
    P_bar: float = Query(..., ge=1, le=300, description="pressure [bar]"),
    T_C: float = Query(..., ge=-20, le=700, description="temperature [\u00b0C]"),
    m_tph: float = Query(..., gt=0, le=2000, description="total steam mass flow [t/h]"),
    tubes: int = Query(DEFAULT_GEOMETRY.n_tubes, ge=1, le=2000, description="parallel tube count"),
    method: HtcMethod = Query(HtcMethod.gnielinski, description="turbulent correlation"),
) -> dict:
    """Re, Pr, Nu (both correlations), friction factor and h for the platen tubes."""
    return htc_mod.htc(
        m_tph=m_tph,
        p_bar=P_bar,
        t_c=T_C,
        d_i_m=DEFAULT_GEOMETRY.d_i_m,
        n_tubes=tubes,
        method=method.value,
    )
