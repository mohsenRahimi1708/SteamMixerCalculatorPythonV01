"""Unit handling for the Platen Superheater Digital Twin.

Contract (enforced across the whole project):
    mass flow      -> t/h
    temperature    -> degC
    pressure       -> bar
    heat rate      -> MW
    heat transfer  -> W/(m2.K)

The solver internals use SI (kg/s, K, Pa).  Conversion happens only at the
boundary: :func:`to_si_*` when entering the physics, :func:`from_si_*` when
leaving it.  No other unit may appear in a payload, chart axis or log line.
"""

from __future__ import annotations

FLOW_UNIT = "t/h"
TEMP_UNIT = "\u00b0C"
PRESS_UNIT = "bar"
POWER_UNIT = "MW"
HTC_UNIT = "W/m\u00b2K"
ENTHALPY_UNIT = "kJ/kg"
VISCOSITY_UNIT = "Pa\u00b7s"
CONDUCTIVITY_UNIT = "W/(m\u00b7K)"
CP_UNIT = "kJ/(kg\u00b7K)"

# --- conversion factors ---------------------------------------------------
HOUR_S = 3600.0
TPH_TO_KGS = 1.0 / 3.6
BAR_TO_PA = 1.0e5
BAR_TO_MPA = 0.1
MW_TO_W = 1.0e6
C_TO_K_OFFSET = 273.15

# --- validation envelope (API contract, not the IF97 envelope) ------------
TEMP_MIN_C = -20.0
TEMP_MAX_C = 700.0
PRESS_MIN_BAR = 1.0
PRESS_MAX_BAR = 300.0
FLOW_MIN_TPH = 0.0
FLOW_MAX_TPH = 2000.0


def tph_to_kgs(m_tph: float) -> float:
    """Convert a mass flow from t/h to kg/s."""
    return m_tph * TPH_TO_KGS


def kgs_to_tph(m_kgs: float) -> float:
    """Convert a mass flow from kg/s to t/h."""
    return m_kgs * HOUR_S / 1000.0


def bar_to_pa(p_bar: float) -> float:
    """Convert a pressure from bar to Pa."""
    return p_bar * BAR_TO_PA


def pa_to_bar(p_pa: float) -> float:
    """Convert a pressure from Pa to bar."""
    return p_pa / BAR_TO_PA


def bar_to_mpa(p_bar: float) -> float:
    """Convert a pressure from bar to MPa (IF97 library boundary)."""
    return p_bar * BAR_TO_MPA


def mpa_to_bar(p_mpa: float) -> float:
    """Convert a pressure from MPa to bar."""
    return p_mpa / BAR_TO_MPA


def c_to_k(t_c: float) -> float:
    """Convert a temperature from degC to K."""
    return t_c + C_TO_K_OFFSET


def k_to_c(t_k: float) -> float:
    """Convert a temperature from K to degC."""
    return t_k - C_TO_K_OFFSET


def mw_to_w(q_mw: float) -> float:
    """Convert a heat rate from MW to W."""
    return q_mw * MW_TO_W


def w_to_mw(q_w: float) -> float:
    """Convert a heat rate from W to MW."""
    return q_w / MW_TO_W


def in_envelope(t_c: float, p_bar: float) -> bool:
    """Return True when a (pressure, temperature) pair is inside the input envelope."""
    return TEMP_MIN_C <= t_c <= TEMP_MAX_C and PRESS_MIN_BAR <= p_bar <= PRESS_MAX_BAR
