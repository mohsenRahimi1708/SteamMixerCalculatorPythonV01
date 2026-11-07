"""Transient endpoint and the shared initial-state resolver."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.core.errors import DomainError
from app.core.logging import get_logger
from app.db.models import RunStore
from app.models.schemas import TransientRequest, TransientResponse
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.init_state import build_initial_state
from app.thermo.platen_transient import solve_transient

router = APIRouter(tags=["transient"])
logger = get_logger("api.transient")


def resolve_initial_state(request: TransientRequest, store: RunStore) -> dict:
    """Map the API request onto a validated initial state."""
    previous_run = None
    if request.initial_mode.value == "previous_run":
        record = store.get(request.previous_run_id or "")
        if record is None:
            raise DomainError(
                "previous_run_not_found", context={"previous_run_id": request.previous_run_id}
            )
        payload = record.payload
        previous_run = {
            "T_metal_C": record.T_metal_C,
            "Q_platen_MW": record.Q_platen_MW,
            "m_tph": record.m_tph,
            "T_in_C": record.T_in_C,
            "run_id": record.id,
            "payload_metal_C": payload.get("T_metal_C"),
            "payload_heat_MW": payload.get("Q_platen_MW"),
        }
    return build_initial_state(
        mode=request.initial_mode.value,
        base={
            "m_main_tph": request.m_main_tph,
            "T_main_C": request.T_main_C,
            "P_bar": request.P_main_bar,
            "m_spray_tph": request.m_spray_tph,
            "T_LT_out_C": request.T_LT_out_C,
        },
        t_metal_init_c=request.T_metal_init_C,
        q_platen_init_mw=request.Q_platen_init_MW,
        previous_run=previous_run,
        geometry=DEFAULT_GEOMETRY,
        htc_method=request.htc_method.value,
        heating=request.heating,
    )


@router.post("/api/transient", response_model=TransientResponse, summary="Single-node transient run")
def transient(request: TransientRequest, store: RunStore = Depends(get_store)) -> dict:
    """March the lumped platen node and return the full time series."""
    started = time.perf_counter()
    initial_state = resolve_initial_state(request, store)
    result = solve_transient(
        m_main_tph=request.m_main_tph,
        t_main_c=request.T_main_C,
        p_bar=request.P_main_bar,
        m_spray_tph=request.m_spray_tph,
        t_lt_out_c=request.T_LT_out_C,
        geometry=DEFAULT_GEOMETRY,
        dt_s=request.dt_s,
        duration_s=request.duration_s,
        initial_state=initial_state,
        q_gas_of_t=None,
        htc_method=request.htc_method.value,
        heating=request.heating,
        n_nodes=request.n_nodes,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "transient_solved",
        extra={
            "elapsed_ms": round(elapsed_ms, 2),
            "n_steps": result["n_steps"],
            "duration_s": request.duration_s,
            "tau_s": round(result["tau_s"], 2),
        },
    )
    return result
