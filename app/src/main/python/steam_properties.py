"""
Thin wrapper around pyXSteam for IAPWS-IF97 steam/water properties.

All validity checks happen here. Every call is wrapped in try/except
and converts exceptions into structured error dicts.
"""

from pyXSteam.XSteam import XSteam

# Shared XSteam instance — MKS units (bar, °C, kJ/kg)
_steam = XSteam(XSteam.UNIT_SYSTEM_MKS)

# ─── Validity domain constants ─────────────────────────────────────────────

PRESSURE_MIN_BAR = 0.006112  # Triple point pressure
PRESSURE_MAX_BAR = 220.64    # Critical pressure
TEMPERATURE_MIN_C = 0.01     # Triple point temperature
TEMPERATURE_MAX_C = 800.0    # Practical upper limit for superheated steam


def _safe(fn, *args):
    """Call fn(*args), returning (result, None) or (None, error_dict)."""
    try:
        result = fn(*args)
        if result is None or result != result:  # NaN check
            return None, {"status": "error", "message": f"pyXSteam returned invalid value for args {args}"}
        return result, None
    except Exception as e:
        return None, {"status": "error", "message": str(e)}


def h_pt(pressure_bar, temperature_c):
    """Enthalpy from pressure (bar) and temperature (°C). [kJ/kg]"""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    if temperature_c < TEMPERATURE_MIN_C or temperature_c > TEMPERATURE_MAX_C:
        return None, {"status": "error", "message": f"Temperature {temperature_c} °C outside valid range ({TEMPERATURE_MIN_C}–{TEMPERATURE_MAX_C})"}
    return _safe(_steam.h_pt, pressure_bar, temperature_c)


def t_ph(pressure_bar, enthalpy_kj_kg):
    """Temperature from pressure (bar) and enthalpy (kJ/kg). [°C] — backward equation."""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    return _safe(_steam.t_ph, pressure_bar, enthalpy_kj_kg)


def tsat_p(pressure_bar):
    """Saturation temperature at given pressure (bar). [°C]"""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    return _safe(_steam.tsat_p, pressure_bar)
