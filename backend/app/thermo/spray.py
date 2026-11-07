"""Desuperheater spray mixing.

First-stage (and second-stage) spray water is saturated liquid at the live
steam pressure, so the mixing is a pure adiabatic enthalpy balance:

    h_main  = h(P, T_main)
    h_spray = h_f(P)                      region 1, x = 0
    h_mix   = (m_main*h_main + m_spray*h_spray) / (m_main + m_spray)
    T_in    = T(P, h_mix)
"""

from __future__ import annotations

from app.core.errors import DomainError
from app.thermo import if97


def mix_spray(
    m_main_tph: float,
    t_main_c: float,
    p_bar: float,
    m_spray_tph: float,
    h_lt_out_kj_kg: float | None = None,
    t_lt_out_c: float | None = None,
) -> dict:
    """Adiabatic mixing of main steam with desuperheater spray water.

    All flows are t/h, temperatures degC, pressure bar.  ``h_lt_out_kj_kg`` or
    ``t_lt_out_c`` are optional diagnostics of the low-temperature superheater
    outlet state used for the reported spray temperature drop.
    """
    if m_main_tph <= 0:
        raise DomainError("invalid_flow", context={"m_main_tph": m_main_tph})
    if m_spray_tph < 0:
        raise DomainError("negative_spray", context={"m_spray_tph": m_spray_tph})

    h_main = if97.h_pt(p_bar, t_main_c)
    h_spray = if97.sat_liquid_h(p_bar)
    m_total_tph = m_main_tph + m_spray_tph
    h_mix = (m_main_tph * h_main + m_spray_tph * h_spray) / m_total_tph
    t_platen_in_c = if97.t_ph(p_bar, h_mix)

    result: dict = {
        "h_main_kJ_kg": h_main,
        "h_spray_kJ_kg": h_spray,
        "h_mix_kJ_kg": h_mix,
        "m_total_tph": m_total_tph,
        "T_platen_in_C": t_platen_in_c,
        "P_bar": p_bar,
        "T_main_C": t_main_c,
        "m_main_tph": m_main_tph,
        "m_spray_tph": m_spray_tph,
    }
    if h_lt_out_kj_kg is not None:
        t_lt = if97.t_ph(p_bar, h_lt_out_kj_kg)
        result["T_LT_out_C"] = t_lt
        result["deltaT_spray_C"] = t_lt - t_platen_in_c
    elif t_lt_out_c is not None:
        result["deltaT_spray_C"] = t_lt_out_c - t_platen_in_c
    return result
