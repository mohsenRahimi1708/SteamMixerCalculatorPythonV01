"""Single-node (N = 1) lumped transient model of the platen superheater.

Governing equations
-------------------
Steam (quasi-steady, mean-temperature reference):

    T_out(t) = T_in(t) + h(t)*A*(T_m(t) - T_bar_s(t)) / (m_dot*cp)
    T_bar_s  = (T_in + T_out) / 2          -> solved in closed form

Metal (explicit Euler, sub-stepped to respect dt <= 0.5*M_m*C_m/(h*A)):

    Q_conv(t) = h(t)*A*(T_bar_s(t) - T_m(t))
    dT_m/dt   = (Q_gas(t) + Q_conv(t)) / (M_m*C_m)

The multi-node (N > 1) discretisation is architecturally reserved: the solver
validates ``n_nodes`` and raises ``n_nodes_unsupported`` until Phase 2 lands.
"""

from __future__ import annotations

import math
from typing import Callable

from app.core.errors import DomainError
from app.thermo import if97, spray
from app.thermo.geometry import DEFAULT_GEOMETRY, PlatenGeometry
from app.thermo.platen_ss import implicit_outlet_temperature, steam_to_metal_ntu

MAX_STEPS = 20000


def _warnings_from(series: dict, geometry: PlatenGeometry) -> list[str]:
    """Operational warning flags for a completed transient run."""
    warnings: list[str] = []
    t_metal = series["T_metal_C"]
    t_out = series["T_out_C"]
    time = series["time_s"]
    if t_metal and max(t_metal) > 600.0:
        warnings.append(
            f"Metal temperature reached {max(t_metal):.1f} degC: above the 600 degC alarm limit."
        )
    d_max = 0.0
    for i in range(1, len(t_out)):
        dt = time[i] - time[i - 1]
        if dt > 0:
            d_max = max(d_max, abs(t_out[i] - t_out[i - 1]) / dt * 60.0)
    if d_max > 5.0:
        warnings.append(
            f"Outlet temperature ramp {d_max:.1f} degC/min exceeds 5 degC/min: thermal stress risk."
        )
    regimes = set(series["regime"])
    if "laminar" in regimes:
        warnings.append(
            "Re dropped into the laminar regime at low load: convection collapses and metal temperature rises."
        )
    elif "transition" in regimes:
        warnings.append(
            "Re entered the transition regime: the heat transfer coefficient is uncertain in this band."
        )
    return warnings


def _settling_time(time: list[float], values: list[float], fraction: float) -> float | None:
    """First time the signal settles within ``fraction`` of its total change."""
    if len(values) < 2:
        return None
    initial, final = values[0], values[-1]
    span = abs(final - initial)
    if span < 0.05:
        return None
    threshold = fraction * span
    for t, value in zip(time, values):
        if abs(final - value) <= threshold:
            return t
    return None


def solve_transient(
    m_main_tph: float,
    t_main_c: float,
    p_bar: float,
    m_spray_tph: float,
    t_lt_out_c: float,
    geometry: PlatenGeometry = DEFAULT_GEOMETRY,
    dt_s: float = 2.0,
    duration_s: float = 600.0,
    initial_state: dict | None = None,
    q_gas_of_t: Callable[[float], float] | None = None,
    htc_method: str = "gnielinski",
    heating: bool = True,
    n_nodes: int = 1,
) -> dict:
    """March the lumped platen model through ``duration_s`` seconds.

    ``q_gas_of_t`` returns the gas-side heat input [MW] at a given time [s];
    when omitted the initial-state heat input is held constant.
    Units in the returned series: t/h, degC, bar, MW, W/(m2*K).
    """
    if n_nodes != 1:
        raise DomainError(
            "n_nodes_unsupported", context={"n_nodes": n_nodes}
        )
    if dt_s <= 0 or duration_s <= 0:
        raise DomainError("invalid_dt", context={"dt_s": dt_s, "duration_s": duration_s})
    if dt_s > duration_s:
        raise DomainError("invalid_dt", context={"dt_s": dt_s, "duration_s": duration_s})
    if initial_state is None:
        raise DomainError("initial_state_inconsistent", "Initial state is required.")

    mixed = spray.mix_spray(
        m_main_tph=m_main_tph,
        t_main_c=t_main_c,
        p_bar=p_bar,
        m_spray_tph=m_spray_tph,
        t_lt_out_c=t_lt_out_c,
    )
    t_in_c = mixed["T_platen_in_C"]
    m_total_tph = mixed["m_total_tph"]
    m_dot_kgs = m_total_tph / 3.6
    area = geometry.inner_area_m2
    capacity = geometry.metal_capacity_j_k

    q0_mw = float(initial_state["Q_platen_MW"])
    if q_gas_of_t is None:
        q_gas_of_t = lambda _t: q0_mw  # noqa: E731

    n_steps = int(round(duration_s / dt_s))
    if n_steps > MAX_STEPS:
        raise DomainError(
            "invalid_dt",
            f"At most {MAX_STEPS} time steps are allowed per run.",
            f"\u062d\u062f\u0627\u06a9\u062b\u0631 {MAX_STEPS} \u06af\u0627\u0645 \u0632\u0645\u0627\u0646\u06cc \u062f\u0631 \u0647\u0631 \u0627\u062c\u0631\u0627 \u0645\u062c\u0627\u0632 \u0627\u0633\u062a.",
            context={"n_steps": n_steps, "dt_s": dt_s},
        )

    t_metal = float(initial_state["T_metal_C"])
    t_out_prev = float(initial_state.get("T_out_C", t_in_c))
    series: dict[str, list] = {
        "time_s": [],
        "T_in_C": [],
        "T_out_C": [],
        "T_metal_C": [],
        "Q_MW": [],
        "Q_gas_MW": [],
        "Q_steam_MW": [],
        "Q_conv_MW": [],
        "Re": [],
        "Pr": [],
        "Nu": [],
        "h_W_m2K": [],
        "regime": [],
    }
    warnings: list[str] = []
    substeps_max = 1
    initial_dTdt = 0.0
    nan_guard = False

    for step in range(n_steps + 1):
        t_now = step * dt_s
        q_gas_mw = float(q_gas_of_t(t_now))

        t_eval = 0.5 * (t_in_c + t_out_prev)
        t_eval = min(max(t_eval, if97.T_MIN_C + 0.5), if97.T_MAX_C - 1.0)
        ntu, diag = steam_to_metal_ntu(m_total_tph, p_bar, t_eval, geometry, htc_method)
        t_out = implicit_outlet_temperature(t_in_c, t_metal, ntu)
        t_mean_steam = 0.5 * (t_in_c + t_out)
        conductance = diag["h_W_m2K"] * area  # W/K
        q_conv_w = conductance * (t_mean_steam - t_metal)  # + to steam
        q_steam_mw = conductance * (t_metal - t_mean_steam) / 1e6

        series["time_s"].append(round(t_now, 6))
        series["T_in_C"].append(t_in_c)
        series["T_out_C"].append(t_out)
        series["T_metal_C"].append(t_metal)
        series["Q_MW"].append(q_gas_mw)
        series["Q_gas_MW"].append(q_gas_mw)
        series["Q_steam_MW"].append(q_steam_mw)
        series["Q_conv_MW"].append(q_conv_w / 1e6)
        series["Re"].append(diag["Re"])
        series["Pr"].append(diag["Pr"])
        series["Nu"].append(diag["Nu"])
        series["h_W_m2K"].append(diag["h_W_m2K"])
        series["regime"].append(diag["regime"])

        if step == 0:
            initial_dTdt = (q_gas_mw * 1e6 + q_conv_w) / capacity

        if step == n_steps:
            t_out_prev = t_out
            break

        # --- explicit Euler with stability-driven sub-stepping -------------
        dt_limit = 0.5 * capacity / conductance if conductance > 0 else math.inf
        substeps = 1 if not math.isfinite(dt_limit) else max(1, int(math.ceil(dt_s / dt_limit)))
        substeps = min(substeps, 400)
        substeps_max = max(substeps_max, substeps)
        d_dt = dt_s / substeps
        if not math.isfinite(conductance):
            nan_guard = True
        for _ in range(substeps):
            t_metal += d_dt * (q_gas_mw * 1e6 + q_conv_w) / capacity
        if not math.isfinite(t_metal) or t_metal < -100.0 or t_metal > 1500.0:
            raise DomainError(
                "out_of_envelope",
                "The transient solution diverged; reduce the time step.",
                "\u062d\u0644 \u0634\u0628\u06cc\u0647\u200c\u0633\u0627\u0632\u06cc \u0648\u0627\u06af\u0631\u0627 \u0634\u062f\u061b \u06af\u0627\u0645 \u0632\u0645\u0627\u0646\u06cc \u0631\u0627 \u06a9\u0627\u0647\u0634 \u062f\u0647\u06cc\u062f.",
                context={"T_metal_C": t_metal, "t_s": t_now},
            )
        t_out_prev = t_out

    warnings.extend(_warnings_from(series, geometry))
    if nan_guard:
        warnings.append("Non-finite conductance detected; results are not trustworthy.")
    if substeps_max > 1:
        warnings.append(
            f"Internal sub-stepping was used ({substeps_max} sub-steps per output step) to keep the explicit Euler metal update stable."
        )

    tau_eff = geometry.tau_s(m_total_tph, p_bar, 0.5 * (t_in_c + series["T_out_C"][-1]))
    t63 = _settling_time(series["time_s"], series["T_out_C"], 0.37)
    t95 = _settling_time(series["time_s"], series["T_out_C"], 0.05)

    return {
        **series,
        "tau_s": tau_eff,
        "t63_s": t63,
        "t95_s": t95,
        "duration_s": duration_s,
        "dt_s": dt_s,
        "n_steps": n_steps,
        "substeps_max": substeps_max,
        "warnings": warnings,
        "initial_state": initial_state,
        "initial_dTdt_C_per_s": initial_dTdt,
        "T_in_C_value": t_in_c,
        "m_total_tph": m_total_tph,
        "P_bar": p_bar,
        "htc_method": htc_method,
        "n_nodes": n_nodes,
        "geometry": geometry.as_dict(),
    }
