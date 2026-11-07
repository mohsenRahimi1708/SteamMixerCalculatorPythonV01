"""Dynamic steam-side heat transfer coefficient.

Every solver step recomputes h from local IF97 properties:

    m_dot_tube = (m_main + m_spray) / (panels * tubes_per_panel)   [kg/s]
    Re         = 4 * m_dot_tube / (pi * d_i * mu)
    Pr         = mu * cp / k
    regime     = laminar (< 2300) | transition (2300 .. 10000) | turbulent (>= 10000)
    Nu         = 4.36 (laminar, constant heat flux)
                 log-linear interpolation across the transition band
                 Dittus-Boelter or Gnielinski (turbulent)
    h          = Nu * k / d_i                                       [W/(m2*K)]
"""

from __future__ import annotations

import math
from typing import Literal

from app.core.errors import DomainError
from app.core.units import tph_to_kgs
from app.thermo import if97

HtcMethod = Literal["dittus_boelter", "gnielinski"]

RE_LAMINAR_MAX = 2300.0
RE_TURBULENT_MIN = 10000.0
NU_LAMINAR = 4.36  # fully developed laminar flow, constant wall heat flux


def reynolds(m_dot_tube_kgs: float, d_i_m: float, mu_pas: float) -> float:
    """Tube-side Reynolds number, Re = 4*m_dot/(pi*d_i*mu)."""
    if d_i_m <= 0 or mu_pas <= 0:
        raise DomainError("invalid_geometry", context={"d_i_m": d_i_m, "mu_Pas": mu_pas})
    return 4.0 * m_dot_tube_kgs / (math.pi * d_i_m * mu_pas)


def prandtl(mu_pas: float, cp_kj_kgk: float, k_w_mk: float) -> float:
    """Prandtl number, Pr = mu*cp/k (cp given in kJ/(kg*K))."""
    if k_w_mk <= 0:
        raise DomainError("invalid_geometry", context={"k_W_mK": k_w_mk})
    return mu_pas * cp_kj_kgk * 1000.0 / k_w_mk


def regime(re_number: float) -> str:
    """Classify the flow regime from the Reynolds number."""
    if re_number < RE_LAMINAR_MAX:
        return "laminar"
    if re_number < RE_TURBULENT_MIN:
        return "transition"
    return "turbulent"


def nusselt_db(re_number: float, pr_number: float, heating: bool = True) -> float:
    """Dittus-Boelter correlation, Nu = 0.023*Re^0.8*Pr^n."""
    n = 0.4 if heating else 0.3
    return 0.023 * (re_number ** 0.8) * (pr_number ** n)


def friction_factor(re_number: float) -> float:
    """Gnielinski (Petukhov) friction factor f = (0.79*ln(Re) - 1.64)^-2."""
    if re_number <= 1.0:
        raise DomainError("invalid_geometry", context={"Re": re_number})
    return (0.79 * math.log(re_number) - 1.64) ** -2


def nusselt_gnielinski(re_number: float, pr_number: float) -> float:
    """Gnielinski correlation for turbulent tube flow."""
    f = friction_factor(re_number)
    eighths = f / 8.0
    numerator = eighths * (re_number - 1000.0) * pr_number
    denominator = 1.0 + 12.7 * math.sqrt(eighths) * (pr_number ** (2.0 / 3.0) - 1.0)
    return numerator / denominator


def nusselt_turbulent(re_number: float, pr_number: float, method: HtcMethod, heating: bool = True) -> float:
    """Turbulent Nusselt number for the selected correlation."""
    if method == "dittus_boelter":
        return nusselt_db(re_number, pr_number, heating)
    if method == "gnielinski":
        if re_number <= 2300.0:
            return NU_LAMINAR
        return max(nusselt_gnielinski(re_number, pr_number), NU_LAMINAR)
    raise DomainError("unknown_htc_method", context={"method": method})


def nusselt(re_number: float, pr_number: float, method: HtcMethod = "gnielinski", heating: bool = True) -> float:
    """Regime-aware Nusselt number.

    The transition band is interpolated log-linearly between the laminar value
    at Re = 2300 and the turbulent value at Re = 10000, so h stays continuous
    across the regime boundaries.
    """
    flow = regime(re_number)
    if flow == "laminar":
        return NU_LAMINAR
    if flow == "turbulent":
        return nusselt_turbulent(re_number, pr_number, method, heating)
    nu_low = NU_LAMINAR
    nu_high = nusselt_turbulent(RE_TURBULENT_MIN, pr_number, method, heating)
    weight = (math.log(re_number) - math.log(RE_LAMINAR_MAX)) / (
        math.log(RE_TURBULENT_MIN) - math.log(RE_LAMINAR_MAX)
    )
    weight = min(max(weight, 0.0), 1.0)
    return math.exp(math.log(nu_low) + weight * (math.log(nu_high) - math.log(nu_low)))


def htc_from_props(
    props: dict,
    m_total_tph: float,
    d_i_m: float,
    n_tubes: int,
    method: HtcMethod = "gnielinski",
    heating: bool = True,
) -> dict:
    """Heat transfer coefficient from an already evaluated IF97 property set."""
    if n_tubes <= 0 or d_i_m <= 0:
        raise DomainError("invalid_geometry", context={"n_tubes": n_tubes, "d_i_m": d_i_m})
    m_total_kgs = tph_to_kgs(m_total_tph)
    m_dot_tube = m_total_kgs / n_tubes
    mu = float(props["mu"])
    k = float(props["k"])
    cp = float(props["cp"])
    re_number = reynolds(m_dot_tube, d_i_m, mu)
    pr_number = prandtl(mu, cp, k)
    nu = nusselt(re_number, pr_number, method, heating)
    nu_db = nusselt_db(re_number, pr_number, heating)
    nu_gn = nusselt_gnielinski(re_number, pr_number) if re_number > 2300.0 else NU_LAMINAR
    f = friction_factor(re_number) if re_number > 1.0 else 0.0
    h_w_m2k = nu * k / d_i_m
    return {
        "Re": re_number,
        "Pr": pr_number,
        "Nu": nu,
        "Nu_DB": nu_db,
        "Nu_Gnielinski": nu_gn,
        "Nu_laminar": NU_LAMINAR,
        "f": f,
        "h_W_m2K": h_w_m2k,
        "regime": regime(re_number),
        "mu_Pas": mu,
        "k_W_mK": k,
        "cp_kJ_kgK": cp,
        "m_dot_tube_tph": m_dot_tube * 3.6,
        "m_total_tph": m_total_tph,
        "n_tubes": n_tubes,
        "d_i_m": d_i_m,
        "method": method,
        "heating": heating,
    }


def htc(
    m_tph: float,
    p_bar: float,
    t_c: float,
    d_i_m: float,
    n_tubes: int,
    method: HtcMethod = "gnielinski",
    heating: bool = True,
) -> dict:
    """Heat transfer coefficient for flow of (P, T, m) through ``n_tubes`` tubes."""
    if m_tph < 0:
        raise DomainError("invalid_flow", context={"m_tph": m_tph})
    if method not in ("dittus_boelter", "gnielinski"):
        raise DomainError("unknown_htc_method", context={"method": method}, status_code=400)
    props = if97.props_pt(p_bar, t_c)
    result = htc_from_props(props, m_tph, d_i_m, n_tubes, method, heating)
    result["P_bar"] = p_bar
    result["T_C"] = t_c
    return result


def max_stable_dt(capacity_j_k: float, h_w_m2k: float, area_m2: float) -> float:
    """Explicit Euler stability limit, dt <= 0.5*M*C/(h*A).

    Returns +inf when the convective term is negligible.
    """
    conductance = h_w_m2k * area_m2
    if conductance <= 0:
        return math.inf
    return 0.5 * capacity_j_k / conductance
