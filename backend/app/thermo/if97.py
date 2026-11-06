"""IAPWS-IF97 water and steam properties.

The industrial formulation IF97 is evaluated by the pure-Python ``iapws``
implementation (IAPWS-IF97 for the thermodynamic surface, IAPWS 2008 for
viscosity and IAPWS 2011 for thermal conductivity, which are the transport
correlations referenced by IF97 releases).

Units at this boundary:
    input   P [bar], T [degC], h [kJ/kg]
    output  h [kJ/kg], s [kJ/(kg*K)], cp [kJ/(kg*K)], rho [kg/m3],
            mu [Pa*s], k [W/(m*K)]
"""

from __future__ import annotations

import math
from functools import lru_cache

from iapws import IAPWS97
from iapws._iapws import _ThCond, _Viscosity

from app.core.errors import DomainError, If97RangeError
from app.core.units import (
    C_TO_K_OFFSET,
    bar_to_mpa,
    c_to_k,
    k_to_c,
    mpa_to_bar,
)

# IF97 validity window used by this application.
T_MIN_C = 0.01
T_MAX_C = 800.0
P_MIN_BAR = 0.006112
P_MAX_BAR = 1000.0


def _check(p_bar: float, t_c: float) -> None:
    """Raise :class:`If97RangeError` when a state point is outside IF97."""
    if not (p_bar == p_bar) or not (t_c == t_c):  # NaN guard
        raise If97RangeError(p_bar, t_c, "non-finite input")
    if p_bar < P_MIN_BAR or p_bar > P_MAX_BAR:
        raise If97RangeError(p_bar, t_c, "pressure outside IF97 envelope")
    if t_c < T_MIN_C or t_c > T_MAX_C:
        raise If97RangeError(p_bar, t_c, "temperature outside IF97 envelope")


def _state_pt(p_bar: float, t_c: float) -> IAPWS97:
    """Build an IF97 state from pressure [bar] and temperature [degC]."""
    _check(p_bar, t_c)
    try:
        state = IAPWS97(P=bar_to_mpa(p_bar), T=c_to_k(t_c))
    except Exception as exc:  # library raises its own exception hierarchy
        raise If97RangeError(p_bar, t_c, type(exc).__name__ + ": " + str(exc)) from exc
    if state is None or state.h is None or state.rho is None:
        raise If97RangeError(p_bar, t_c, "no solution returned")
    return state


def _state_ph(p_bar: float, h_kj_kg: float) -> IAPWS97:
    """Build an IF97 state from pressure [bar] and specific enthalpy [kJ/kg]."""
    if p_bar < P_MIN_BAR or p_bar > P_MAX_BAR:
        raise DomainError(
            "out_of_if97_range",
            context={"P_bar": p_bar, "detail": "pressure outside IF97 envelope"},
        )
    try:
        state = IAPWS97(P=bar_to_mpa(p_bar), h=float(h_kj_kg))
        if state is not None and state.T is not None:
            return state
    except Exception:
        pass
    # Fallback: monotone inversion of h(P, T) over the IF97 temperature range.
    return _state_ph_bisect(p_bar, h_kj_kg)


def _state_ph_bisect(p_bar: float, h_kj_kg: float, tol: float = 1e-6) -> IAPWS97:
    """Invert h(P, T) by bisection when the IF97 backward equation fails."""
    lo, hi = T_MIN_C, T_MAX_C
    h_lo = h_pt(p_bar, lo)
    h_hi = h_pt(p_bar, hi)
    if not (h_lo <= h_kj_kg <= h_hi):
        raise DomainError(
            "out_of_if97_range",
            context={"P_bar": p_bar, "h_kJ_kg": h_kj_kg, "detail": "enthalpy outside IF97 envelope"},
        )
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if h_pt(p_bar, mid) < h_kj_kg:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return _state_pt(p_bar, 0.5 * (lo + hi))


def _transport(rho: float, t_k: float, region: int | None) -> tuple[float, float]:
    """Viscosity [Pa*s] and thermal conductivity [W/(m*K)] for a state."""
    # fase=None keeps iapws on the standard IAPWS 2008/2011 correlations; passing a
    # phase string switches on its critical-enhancement branch which needs extra state.
    mu = _Viscosity(rho, t_k)
    k = _ThCond(rho, t_k)
    if isinstance(mu, (tuple, list)):
        mu = mu[0]
    if isinstance(k, (tuple, list)):
        k = k[0]
    return float(mu), float(k)


@lru_cache(maxsize=8192)
def _props_cached(p_bar: float, t_c: float) -> dict[str, float | int | None]:
    """Cached property evaluation; keys are rounded to solver resolution."""
    state = _state_pt(p_bar, t_c)
    region = int(state.region) if state.region else None
    mu, k = _transport(float(state.rho), float(state.T), region)
    return {
        "region": region,
        "rho": float(state.rho),
        "v": float(state.v),
        "h": float(state.h),
        "s": float(state.s),
        "cp": float(state.cp),
        "mu": mu,
        "k": k,
        "w": float(state.w) if state.w is not None else 0.0,
        "T_C": t_c,
        "P_bar": p_bar,
    }


def props_pt(p_bar: float, t_c: float) -> dict[str, float | int | None]:
    """Full IF97 property set at (P [bar], T [degC])."""
    return dict(_props_cached(round(float(p_bar), 6), round(float(t_c), 6)))


def h_pt(p_bar: float, t_c: float) -> float:
    """Specific enthalpy [kJ/kg] from pressure [bar] and temperature [degC]."""
    return float(_props_cached(round(float(p_bar), 6), round(float(t_c), 6))["h"])


def t_ph(p_bar: float, h_kj_kg: float) -> float:
    """Temperature [degC] from pressure [bar] and enthalpy [kJ/kg] (IF97 backward)."""
    state = _state_ph(p_bar, h_kj_kg)
    return k_to_c(float(state.T))


def props_ph(p_bar: float, h_kj_kg: float) -> dict[str, float | int | None]:
    """Full IF97 property set at (P [bar], h [kJ/kg])."""
    state = _state_ph(p_bar, h_kj_kg)
    t_c = k_to_c(float(state.T))
    return props_pt(p_bar, t_c)


def sat_liquid_h(p_bar: float) -> float:
    """Saturated-liquid enthalpy [kJ/kg] at pressure [bar] (region 1, x = 0)."""
    _check(p_bar, max(T_MIN_C, 50.0))
    try:
        state = IAPWS97(P=bar_to_mpa(p_bar), x=0)
    except Exception as exc:
        raise If97RangeError(p_bar, 0.0, "saturation: " + str(exc)) from exc
    if state is None or state.h is None:
        raise If97RangeError(p_bar, 0.0, "no saturated liquid solution")
    return float(state.h)


def tsat_p(p_bar: float) -> float:
    """Saturation temperature [degC] at pressure [bar] (IF97 region 4)."""
    _check(p_bar, max(T_MIN_C, 50.0))
    try:
        state = IAPWS97(P=bar_to_mpa(p_bar), x=0)
    except Exception as exc:
        raise If97RangeError(p_bar, 0.0, "saturation: " + str(exc)) from exc
    return k_to_c(float(state.T))


def psat_t(t_c: float) -> float:
    """Saturation pressure [bar] at temperature [degC] (IF97 region 4)."""
    _check(1.0, t_c)
    try:
        state = IAPWS97(T=c_to_k(t_c), x=0)
    except Exception as exc:
        raise If97RangeError(1.0, t_c, "saturation: " + str(exc)) from exc
    return mpa_to_bar(float(state.P))


def region_of(p_bar: float, t_c: float) -> int:
    """IF97 region number for a (P, T) state point."""
    return int(_state_pt(p_bar, t_c).region or 0)


def t_from_h_pt_safe(p_bar: float, h_kj_kg: float) -> tuple[float, bool]:
    """Temperature with a validity flag instead of an exception (used in search loops)."""
    try:
        return t_ph(p_bar, h_kj_kg), True
    except DomainError:
        return math.nan, False


__all__ = [
    "props_pt",
    "props_ph",
    "h_pt",
    "t_ph",
    "sat_liquid_h",
    "tsat_p",
    "psat_t",
    "region_of",
    "T_MIN_C",
    "T_MAX_C",
    "P_MIN_BAR",
    "P_MAX_BAR",
    "C_TO_K_OFFSET",
]
