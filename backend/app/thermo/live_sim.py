"""Live (streaming) burner simulation session.

The WebSocket burner endpoint drives this class: it keeps the N = 1 platen
state in memory, advances it in real time (or at a configurable speed factor),
and applies ``set_burner`` commands at the current simulation time.

All quantities leaving the session use the API units: MW, degC, W/(m2*K), t/h.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.core.errors import DomainError
from app.thermo import burner as burner_mod
from app.thermo import platen_transient
from app.thermo.geometry import DEFAULT_GEOMETRY

DEFAULT_DT_S = 0.5
FRAME_INTERVAL_S = 0.2


@dataclass
class LiveBurnerSession:
    """Stateful live simulation of the platen under burner start/stop."""

    m_main_tph: float
    t_main_c: float
    p_bar: float
    m_spray_tph: float
    t_lt_out_c: float
    initial_state: dict
    q_platen_fraction: float = burner_mod.DEFAULT_Q_PLATEN_FRACTION
    gas_lag_s: float = burner_mod.DEFAULT_GAS_LAG_S
    htc_method: str = "gnielinski"
    speed: float = 1.0
    target_t_out_c: float | None = None
    target_t_metal_c: float | None = None
    schedule: burner_mod.BurnerSchedule = field(default_factory=burner_mod.BurnerSchedule)
    t_s: float = 0.0
    t_metal_c: float = 0.0
    t_out_c: float = 0.0
    last_diag: dict = field(default_factory=dict)
    _started_at: float = 0.0
    _prev_q_gas_mw: float = 0.0

    def __post_init__(self) -> None:
        self.t_metal_c = float(self.initial_state["T_metal_C"])
        self.t_out_c = float(self.initial_state["T_out_C"])
        self._started_at = time.monotonic()
        self._refresh_diagnostics(0.0)

    # --- schedule ---------------------------------------------------------
    def apply_event(self, event: burner_mod.BurnerEvent) -> None:
        """Inject one ignition/shutdown command at the current simulation time."""
        if self.schedule.events and self.t_s < self.schedule.events[-1].time_s:
            # keep the log ordered without rewinding the simulation clock
            pass
        self.schedule.add(event)

    def ignite(self, tag: str, state: str, load: float, ramp_s: float) -> dict:
        """Handle a client ``set_burner`` command."""
        event = burner_mod.BurnerEvent(
            tag=tag,
            time_s=self.t_s,
            state=state,
            target_load_fraction=load,
            ramp_time_s=ramp_s,
        )
        self.apply_event(event)
        payload = event.as_dict()
        payload["simulated_time_s"] = self.t_s
        return payload

    # --- stepping ---------------------------------------------------------
    def _refresh_diagnostics(self, q_gas_mw: float) -> None:
        """Recompute h/Re/Nu at the current operating point."""
        t_eval = 0.5 * (self.t_out_c + self.initial_state.get("T_in_C", self.t_out_c))
        try:
            _, diag = platen_transient.steam_to_metal_ntu(
                self.initial_state["m_total_tph"],
                self.p_bar,
                t_eval,
                DEFAULT_GEOMETRY,
                self.htc_method,
            )
        except DomainError:
            return
        self.last_diag = diag
        self.last_diag["Q_gas_MW"] = q_gas_mw

    def step(self, dt_s: float = DEFAULT_DT_S) -> dict:
        """Advance the simulation by ``dt_s`` simulated seconds."""
        q_gas_mw = self.q_platen_fraction * self.schedule.q_burners_mw(self.t_s - self.gas_lag_s)
        q_gas_mw = max(q_gas_mw, 0.0)
        geometry = DEFAULT_GEOMETRY
        capacity = geometry.metal_capacity_j_k
        t_in_c = float(self.initial_state["T_in_C"])
        conductance = self.last_diag.get("h_W_m2K", 0.0) * geometry.inner_area_m2

        if conductance > 0:
            dt_limit = 0.5 * capacity / conductance
            substeps = max(1, int(dt_s / dt_limit) + 1) if dt_limit < dt_s else 1
        else:
            substeps = 1
        sub_dt = dt_s / substeps
        for _ in range(substeps):
            q_conv_w = conductance * ((0.5 * (t_in_c + self.t_out_c)) - self.t_metal_c)
            self.t_metal_c += sub_dt * (q_gas_mw * 1e6 + q_conv_w) / capacity
            t_eval = 0.5 * (t_in_c + self.t_out_c)
            ntu = conductance / max(1e-9, (self.initial_state["m_total_tph"] / 3.6) * 2600.0)
            self.t_out_c = platen_transient.implicit_outlet_temperature(
                t_in_c, self.t_metal_c, ntu
            )

        self.t_s += dt_s
        self._prev_q_gas_mw = q_gas_mw
        self._refresh_diagnostics(q_gas_mw)
        return self.frame()

    def frame(self) -> dict:
        """Current frame in API units."""
        diag = self.last_diag
        q_burners = self.schedule.q_burners_mw(self.t_s)
        q_gas = self.q_platen_fraction * self.schedule.q_burners_mw(self.t_s - self.gas_lag_s)
        warnings: list[str] = []
        if self.t_metal_c > 600.0:
            warnings.append("T_metal > 600 degC")
        if diag.get("regime") in ("laminar", "transition"):
            warnings.append(f"Re in {diag.get('regime')} regime")
        return {
            "type": "frame",
            "time_s": round(self.t_s, 3),
            "T_in_C": round(float(self.initial_state["T_in_C"]), 3),
            "T_out_C": round(self.t_out_c, 3),
            "T_metal_C": round(self.t_metal_c, 3),
            "Q_burners_MW": round(q_burners, 3),
            "Q_gas_MW": round(max(q_gas, 0.0), 3),
            "Re": diag.get("Re", 0.0),
            "Pr": diag.get("Pr", 0.0),
            "Nu": diag.get("Nu", 0.0),
            "h_W_m2K": diag.get("h_W_m2K", 0.0),
            "regime": diag.get("regime", "unknown"),
            "burners_on": self.schedule.active_count(self.t_s),
            "burner_states": self.schedule.states_at(self.t_s),
            "warnings": warnings,
        }

    @property
    def elapsed_wall_s(self) -> float:
        """Wall-clock seconds since the session started."""
        return time.monotonic() - self._started_at
