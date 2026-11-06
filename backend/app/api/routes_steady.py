"""Steady-state endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.core.logging import get_logger
from app.models.schemas import SteadyRequest, SteadyResponse
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.platen_ss import solve_steady

router = APIRouter(tags=["steady"])
logger = get_logger("api.steady")


@router.post("/api/steady", response_model=SteadyResponse, summary="Steady-state platen prediction")
def steady(request: SteadyRequest) -> dict:
    """Predict platen inlet/outlet temperatures and the tube-side heat transfer."""
    started = time.perf_counter()
    result = solve_steady(
        m_main_tph=request.m_main_tph,
        t_main_c=request.T_main_C,
        p_bar=request.P_main_bar,
        m_spray_tph=request.m_spray_tph,
        t_lt_out_c=request.T_LT_out_C,
        q_platen_mw=request.Q_platen_MW,
        geometry=DEFAULT_GEOMETRY,
        htc_method=request.htc_method.value,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "steady_solved",
        extra={
            "elapsed_ms": round(elapsed_ms, 2),
            "T_platen_out_C": round(result["T_platen_out_C"], 3),
            "h_W_m2K": round(result["h_W_m2K"], 1),
            "regime": result["regime"],
        },
    )
    return result
