"""
Thin wrapper around pyXSteam for IAPWS-IF97 steam/water properties.

All validity checks happen here. pyXSteam is imported lazily
to avoid recursion errors on Python 3.14 in the Android environment.
"""

# Validity domain constants
PRESSURE_MIN_BAR = 0.006112
PRESSURE_MAX_BAR = 220.64
TEMPERATURE_MIN_C = 0.01
TEMPERATURE_MAX_C = 800.0

# Lazy-loaded singleton
_steam = None


def _get_steam():
    """Get or create the XSteam instance (lazy init)."""
    global _steam
    if _steam is None:
        from pyXSteam.XSteam import XSteam
        _steam = XSteam(XSteam.UNIT_SYSTEM_MKS)
    return _steam


def _safe(fn, *args):
    """Call fn(*args), returning (result, None) or (None, error_dict)."""
    try:
        result = fn(*args)
        if result is None or result != result:  # NaN check
            return None, {"status": "error", "message": f"Invalid value for args {args}"}
        return result, None
    except Exception as e:
        return None, {"status": "error", "message": str(e)}


def h_pt(pressure_bar, temperature_c):
    """Enthalpy from pressure (bar) and temperature (°C). [kJ/kg]"""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    if temperature_c < TEMPERATURE_MIN_C or temperature_c > TEMPERATURE_MAX_C:
        return None, {"status": "error", "message": f"Temperature {temperature_c} °C outside valid range ({TEMPERATURE_MIN_C}–{TEMPERATURE_MAX_C})"}
    steam = _get_steam()
    return _safe(steam.h_pt, pressure_bar, temperature_c)


def t_ph(pressure_bar, enthalpy_kj_kg):
    """Temperature from pressure (bar) and enthalpy (kJ/kg). [°C] — backward equation."""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    steam = _get_steam()
    return _safe(steam.t_ph, pressure_bar, enthalpy_kj_kg)


def tsat_p(pressure_bar):
    """Saturation temperature at given pressure (bar). [°C]"""
    if pressure_bar < PRESSURE_MIN_BAR or pressure_bar > PRESSURE_MAX_BAR:
        return None, {"status": "error", "message": f"Pressure {pressure_bar} bar outside valid range ({PRESSURE_MIN_BAR}–{PRESSURE_MAX_BAR})"}
    steam = _get_steam()
    return _safe(steam.tsat_p, pressure_bar)
