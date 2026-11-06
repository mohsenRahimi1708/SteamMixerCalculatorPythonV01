"""Burner start/stop endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.api.deps import get_store
from app.api.routes_transient import resolve_initial_state
from app.core.logging import get_logger
from app.db.models import RunStore
from app.models.schemas import (
    BurnerEventInput,
    BurnerPresetOut,
    BurnerSpecOut,
    BurnerStartupRequest,
    BurnerStartupResponse,
)
from app.thermo import burner as burner_mod
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.platen_transient import solve_transient

router = APIRouter(tags=["burner"])
logger = get_logger("api.burner")


def build_schedule(request: BurnerStartupRequest) -> burner_mod.BurnerSchedule:
    """Turn a request into an ordered burner schedule."""
    if request.burner_schedule:
        events = [
            burner_mod.BurnerEvent(
                tag=item.tag,
                time_s=item.effective_time(),
                state=item.state.value,
                target_load_fraction=item.target_load_fraction,
                ramp_time_s=item.ramp_time_s,
            )
            for item in request.burner_schedule
        ]
        return burner_mod.as_schedule(events)
    preset = request.preset or "four_burners"
    return burner_mod.as_schedule(burner_mod.preset_schedule(preset))


def _first_crossing(time_s: list[float], values: list[float], target: float | None) -> float | None:
    """First time the signal reaches ``target`` in the direction of its change."""
    if target is None or not values:
        return None
    rising = target >= values[0]
    for t, value in zip(time_s, values):
        if (rising and value >= target) or (not rising and value <= target):
            return t
    return None


@router.get("/api/burners", response_model=list[BurnerSpecOut], summary="Burner layout")
def burners() -> list[dict]:
    """All 24 burners with level, row and elevation."""
    return [b.as_dict() for b in burner_mod.BURNERS]


@router.get("/api/burner_presets", response_model=list[BurnerPresetOut], summary="Burner presets")
def presets() -> list[dict]:
    """Named start-up presets available to the burner screen."""
    return burner_mod.preset_catalog()


@router.post(
    "/api/burner_startup",
    response_model=BurnerStartupResponse,
    summary="Burner start/stop transient",
)
def burner_startup(
    request: BurnerStartupRequest, store: RunStore = Depends(get_store)
) -> dict:
    """Simulate a graphical burner start/stop sequence and stream-ready arrays."""
    started = time.perf_counter()
    initial_state = resolve_initial_state(request, store)
    schedule = build_schedule(request)
    q_gas = burner_mod.q_gas_to_platen_of_t(
        schedule,
        q_fraction=request.q_platen_fraction,
        lag_s=request.gas_to_metal_lag_s,
    )
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
        q_gas_of_t=q_gas,
        htc_method=request.htc_method.value,
        heating=request.heating,
        n_nodes=request.n_nodes,
    )
    q_burners = [schedule.q_burners_mw(t) for t in result["time_s"]]
    result["Q_burners_MW"] = q_burners
    result["Q_gas_MW_platen"] = [max(v, 0.0) for v in result["Q_gas_MW"]]
    result["burner_events"] = [event.as_dict() for event in schedule.events]
    result["burner_states_final"] = schedule.states_at(result["time_s"][-1])
    result["t_reach_T_out_s"] = _first_crossing(
        result["time_s"], result["T_out_C"], request.target_T_out_C
    )
    result["t_reach_T_metal_s"] = _first_crossing(
        result["time_s"], result["T_metal_C"], request.target_T_metal_C
    )
    result["q_platen_fraction"] = request.q_platen_fraction
    result["gas_to_metal_lag_s"] = request.gas_to_metal_lag_s
    result["warnings"] = list(result["warnings"])
    if request.target_T_out_C is not None and result["t_reach_T_out_s"] is None:
        result["warnings"].append(
            "Target outlet temperature was not reached within the simulated duration."
        )
    if result["t63_s"] is None:
        result["warnings"].append(
            "No settling time: the outlet change is below 0.05 \u00b0C over this run."
        )
    logger.info(
        "burner_startup_solved",
        extra={
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "events": len(schedule.events),
            "duration_s": request.duration_s,
        },
    )
    return result
