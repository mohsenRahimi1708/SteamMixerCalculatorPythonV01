"""Steady-state platen superheater model.

Chain: main steam + first-stage spray -> platen inlet state -> heat absorption
-> platen outlet state, with the tube-side heat transfer coefficient evaluated
at the mean steam temperature.

    Q [MW] = m_dot [kg/s] * (h_out - h_mix) [kJ/kg] / 1000
    delta_h [kJ/kg] = Q_MW * 3600 / m_total_tph
"""

from __future__ import annotations

from app.core.errors import DomainError
from app.core.units import (
    PRESS_MAX_BAR,
    PRESS_MIN_BAR,
    TEMP_MAX_C,
    TEMP_MIN_C,
)
from app.thermo import htc as htc_mod
from app.thermo import if97, spray
from app.thermo.geometry import DEFAULT_GEOMETRY, PlatenGeometry


def implicit_outlet_temperature(t_in_c: float, t_metal_c: float, ntu: float) -> float:
    """Solve T_out = T_in + NTU*(T_m - (T_in + T_out)/2) for T_out.

    The platen uses the mean steam temperature as its reference, which makes
    the outlet relation implicit.  Solving it in closed form keeps the explicit
    Euler metal update stable for any NTU.
    """
    denominator = 1.0 + 0.5 * ntu
    if denominator <= 0:
        raise DomainError("invalid_geometry", context={"NTU": ntu})
    return (t_in_c * (1.0 - 0.5 * ntu) + ntu * t_metal_c) / denominator


def steam_to_metal_ntu(
    m_total_tph: float,
    p_bar: float,
    t_eval_c: float,
    geometry: PlatenGeometry,
    htc_method: str,
) -> tuple[float, dict]:
    """Return (NTU, heat transfer diagnostics) at the evaluation temperature."""
    props = if97.props_pt(p_bar, t_eval_c)
    diag = htc_mod.htc_from_props(
        props,
        m_total_tph=m_total_tph,
        d_i_m=geometry.d_i_m,
        n_tubes=geometry.n_tubes,
        method=htc_method,  # type: ignore[arg-type]
    )
    cp_j_kgk = float(props["cp"]) * 1000.0
    ntu = diag["h_W_m2K"] * geometry.inner_area_m2 / (
        (m_total_tph / 3.6) * cp_j_kgk
    )
    diag["NTU"] = ntu
    diag["T_eval_C"] = t_eval_c
    return ntu, diag


def solve_steady(
    m_main_tph: float,
    t_main_c: float,
    p_bar: float,
    m_spray_tph: float,
    t_lt_out_c: float,
    q_platen_mw: float,
    geometry: PlatenGeometry = DEFAULT_GEOMETRY,
    htc_method: str = "gnielinski",
    heating: bool = True,
) -> dict:
    """Steady-state platen prediction (all inputs in t/h, degC, bar, MW)."""
    if m_main_tph <= 0:
        raise DomainError("invalid_flow", context={"m_main_tph": m_main_tph})
    if m_spray_tph < 0:
        raise DomainError("negative_spray", context={"m_spray_tph": m_spray_tph})
    if q_platen_mw < 0:
        raise DomainError(
            "out_of_envelope",
            "Heat absorbed by the platen cannot be negative.",
            "\u062d\u0631\u0627\u0631\u062a \u062c\u0630\u0628\u200c\u0634\u062f\u0647 \u062f\u0631 \u067e\u0644\u06cc\u062a\u0646 \u0646\u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u062f \u0645\u0646\u0641\u06cc \u0628\u0627\u0634\u062f.",
            context={"Q_platen_MW": q_platen_mw},
        )
    if not (PRESS_MIN_BAR <= p_bar <= PRESS_MAX_BAR):
        raise DomainError(
            "out_of_envelope",
            f"Pressure must be between {PRESS_MIN_BAR} and {PRESS_MAX_BAR} bar.",
            f"\u0641\u0634\u0627\u0631 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0646 {PRESS_MIN_BAR} \u0648 {PRESS_MAX_BAR} \u0628\u0627\u0631 \u0628\u0627\u0634\u062f.",
            context={"P_bar": p_bar},
        )
    if not (TEMP_MIN_C <= t_main_c <= TEMP_MAX_C):
        raise DomainError(
            "out_of_envelope",
            f"Temperature must be between {TEMP_MIN_C} and {TEMP_MAX_C} degC.",
            f"\u062f\u0645\u0627 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0646 {TEMP_MIN_C} \u0648 {TEMP_MAX_C} \u062f\u0631\u062c\u0647 \u0633\u0627\u0646\u062a\u06cc\u06af\u0631\u0627\u062f \u0628\u0627\u0634\u062f.",
            context={"T_C": t_main_c},
        )

    mixed = spray.mix_spray(
        m_main_tph=m_main_tph,
        t_main_c=t_main_c,
        p_bar=p_bar,
        m_spray_tph=m_spray_tph,
        t_lt_out_c=t_lt_out_c,
    )
    m_total_tph = mixed["m_total_tph"]
    h_mix = mixed["h_mix_kJ_kg"]
    delta_h = q_platen_mw * 3600.0 / m_total_tph
    h_out = h_mix + delta_h
    t_out_c = if97.t_ph(p_bar, h_out)
    if not (TEMP_MIN_C <= t_out_c <= TEMP_MAX_C):
        raise DomainError(
            "out_of_if97_range",
            "Computed platen outlet temperature is outside the IF97 envelope.",
            "\u062f\u0645\u0627\u06cc \u062e\u0631\u0648\u062c\u06cc \u0645\u062d\u0627\u0633\u0628\u0647\u200c\u0634\u062f\u0647 \u062e\u0627\u0631\u062c \u0627\u0632 \u0645\u062d\u062f\u0648\u062f\u0647\u0654 IF97 \u0627\u0633\u062a.",
            context={"T_platen_out_C": t_out_c, "h_out_kJ_kg": h_out},
        )

    t_mean_c = 0.5 * (mixed["T_platen_in_C"] + t_out_c)
    _, diag = steam_to_metal_ntu(m_total_tph, p_bar, t_mean_c, geometry, htc_method)

    warnings: list[str] = []
    if diag["regime"] == "laminar":
        warnings.append(
            "Steam flow is laminar in the platen tubes: the convective coefficient is minimal."
        )
    elif diag["regime"] == "transition":
        warnings.append(
            "Steam flow is in the transition regime: the heat transfer coefficient is not fully developed."
        )
    if t_out_c > 600.0:
        warnings.append("Platen outlet temperature exceeds 600 degC: check the second-stage spray.")

    return {
        "T_platen_in_C": mixed["T_platen_in_C"],
        "T_platen_out_C": t_out_c,
        "deltaT_spray_C": mixed.get("deltaT_spray_C", t_lt_out_c - mixed["T_platen_in_C"]),
        "heat_absorbed_MW": q_platen_mw,
        "Re": diag["Re"],
        "Pr": diag["Pr"],
        "Nu": diag["Nu"],
        "Nu_DB": diag["Nu_DB"],
        "Nu_Gnielinski": diag["Nu_Gnielinski"],
        "f": diag["f"],
        "h_W_m2K": diag["h_W_m2K"],
        "regime": diag["regime"],
        "mu_Pas": diag["mu_Pas"],
        "k_W_mK": diag["k_W_mK"],
        "cp_kJ_kgK": diag["cp_kJ_kgK"],
        "h_main_kJ_kg": mixed["h_main_kJ_kg"],
        "h_spray_kJ_kg": mixed["h_spray_kJ_kg"],
        "h_mix_kJ_kg": h_mix,
        "m_total_tph": m_total_tph,
        "m_main_tph": m_main_tph,
        "m_spray_tph": m_spray_tph,
        "T_main_C": t_main_c,
        "T_LT_out_C": t_lt_out_c,
        "P_bar": p_bar,
        "Q_platen_MW": q_platen_mw,
        "htc_method": htc_method,
        "NTU": diag["NTU"],
        "warnings": warnings,
    }
