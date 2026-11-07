"""WebSocket streaming endpoints.

``/ws/transient``      streams a completed transient frame by frame
``/ws/burner_startup`` runs a live simulation and accepts burner toggles

Frames carry the same field names and units as the REST payloads
(t/h, degC, bar, MW, W/(m2*K)).
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.routes_burner import build_schedule
from app.api.routes_transient import resolve_initial_state
from app.core.config import settings
from app.core.errors import DomainError
from app.core.logging import get_logger
from app.db.models import RunStore
from app.models.schemas import (
    BurnerStartupRequest,
    TransientRequest,
    WsBurnerStart,
    WsToggleCommand,
    WsTransientStart,
)
from app.thermo import burner as burner_mod
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.live_sim import LiveBurnerSession
from app.thermo.platen_transient import solve_transient

router = APIRouter(tags=["websocket"])
logger = get_logger("api.ws")


async def _send_error(websocket: WebSocket, code: str, message: str, extra: dict | None = None) -> None:
    """Send a structured error frame."""
    payload = {"type": "error", "code": code, "message": message}
    if extra:
        payload.update(extra)
    await websocket.send_json(payload)


def _frame_of(result: dict, index: int) -> dict:
    """One compact transient frame."""
    return {
        "type": "frame",
        "index": index,
        "time_s": result["time_s"][index],
        "T_in_C": result["T_in_C"][index],
        "T_out_C": result["T_out_C"][index],
        "T_metal_C": result["T_metal_C"][index],
        "Q_MW": result["Q_MW"][index],
        "Q_steam_MW": result["Q_steam_MW"][index],
        "Re": result["Re"][index],
        "Pr": result["Pr"][index],
        "Nu": result["Nu"][index],
        "h_W_m2K": result["h_W_m2K"][index],
        "regime": result["regime"][index],
    }


@router.websocket("/ws/transient")
async def ws_transient(websocket: WebSocket) -> None:
    """Stream a transient run; the client may send ``{"type": "stop"}`` to abort."""
    await websocket.accept()
    store: RunStore = websocket.app.state.store
    stop = asyncio.Event()

    async def listen() -> None:
        try:
            while True:
                message = await websocket.receive_json()
                if message.get("type") in ("stop", "close"):
                    stop.set()
                    return
        except WebSocketDisconnect:
            stop.set()
        except RuntimeError:
            stop.set()

    listener = asyncio.create_task(listen())
    try:
        raw = await websocket.receive_json()
        try:
            start = WsTransientStart.model_validate(raw)
        except ValidationError as exc:
            await _send_error(websocket, "validation_error", str(exc))
            return
        request: TransientRequest = start.request
        initial_state = resolve_initial_state(request, store)
        result = await asyncio.to_thread(
            solve_transient,
            request.m_main_tph,
            request.T_main_C,
            request.P_main_bar,
            request.m_spray_tph,
            request.T_LT_out_C,
            DEFAULT_GEOMETRY,
            request.dt_s,
            request.duration_s,
            initial_state,
            None,
            request.htc_method.value,
            request.heating,
            request.n_nodes,
        )
        await websocket.send_json(
            {
                "type": "ready",
                "n_frames": len(result["time_s"]),
                "dt_s": result["dt_s"],
                "tau_s": result["tau_s"],
                "warnings": result["warnings"],
            }
        )
        pace = max(0.001, min(0.05, 1.0 / max(start.speed, 1e-6)))
        for index in range(len(result["time_s"])):
            if stop.is_set():
                break
            await websocket.send_json(_frame_of(result, index))
            await asyncio.sleep(pace)
        await websocket.send_json(
            {
                "type": "done",
                "tau_s": result["tau_s"],
                "t63_s": result["t63_s"],
                "t95_s": result["t95_s"],
                "warnings": result["warnings"],
            }
        )
    except WebSocketDisconnect:
        logger.info("ws_transient_client_disconnected")
    except DomainError as exc:
        with contextlib.suppress(RuntimeError):
            await _send_error(websocket, exc.code, exc.message_en, {"detail": exc.to_payload()})
    finally:
        listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener
        with contextlib.suppress(RuntimeError):
            await websocket.close()


@router.websocket("/ws/burner_startup")
async def ws_burner_startup(websocket: WebSocket) -> None:
    """Run the platen live while burners are ignited and shut down."""
    await websocket.accept()
    store: RunStore = websocket.app.state.store
    stop = asyncio.Event()

    try:
        raw = await websocket.receive_json()
        try:
            start = WsBurnerStart.model_validate(raw)
        except ValidationError as exc:
            await _send_error(websocket, "validation_error", str(exc))
            return
        request: BurnerStartupRequest = start.request
        initial_state = resolve_initial_state(request, store)
        session = LiveBurnerSession(
            m_main_tph=request.m_main_tph,
            t_main_c=request.T_main_C,
            p_bar=request.P_main_bar,
            m_spray_tph=request.m_spray_tph,
            t_lt_out_c=request.T_LT_out_C,
            initial_state=initial_state,
            q_platen_fraction=request.q_platen_fraction,
            gas_lag_s=request.gas_to_metal_lag_s,
            htc_method=request.htc_method.value,
            speed=start.speed,
            target_t_out_c=request.target_T_out_C,
            target_t_metal_c=request.target_T_metal_C,
            schedule=build_schedule(request),
        )

        async def listen() -> None:
            try:
                while True:
                    message = await websocket.receive_json()
                    kind = message.get("type", message.get("action"))
                    if kind in ("stop", "close"):
                        stop.set()
                        return
                    if kind == "set_burner":
                        try:
                            command = WsToggleCommand.model_validate(message)
                        except ValidationError as exc:
                            await _send_error(websocket, "validation_error", str(exc))
                            continue
                        event = session.ignite(
                            command.tag,
                            command.state.value,
                            command.target_load_fraction,
                            command.ramp_time_s,
                        )
                        await websocket.send_json({"type": "event_ack", "event": event})
                    elif kind == "get_state":
                        await websocket.send_json(session.frame())
            except WebSocketDisconnect:
                stop.set()
            except RuntimeError:
                stop.set()

        listener = asyncio.create_task(listen())
        await websocket.send_json(
            {
                "type": "ready",
                "burners": [b.as_dict() for b in burner_mod.BURNERS],
                "initial_state": initial_state,
                "dt_s": settings.live_dt_s,
                "speed": start.speed,
                "q_platen_fraction": request.q_platen_fraction,
                "gas_to_metal_lag_s": request.gas_to_metal_lag_s,
            }
        )
        sim_dt = settings.live_dt_s
        while not stop.is_set() and not listener.done():
            frame = session.step(sim_dt)
            await websocket.send_json(frame)
            await asyncio.sleep(max(sim_dt / max(start.speed, 1e-6), 0.02))
        listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener
        with contextlib.suppress(RuntimeError):
            await websocket.send_json({"type": "done", "time_s": session.t_s})
            await websocket.close()
    except WebSocketDisconnect:
        logger.info("ws_burner_client_disconnected")
    except DomainError as exc:
        with contextlib.suppress(RuntimeError):
            await _send_error(websocket, exc.code, exc.message_en, {"detail": exc.to_payload()})
    except RuntimeError:
        logger.info("ws_burner_closed")
