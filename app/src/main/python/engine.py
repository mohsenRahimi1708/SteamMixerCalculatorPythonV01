"""
Chaquopy bridge — entry points called from Kotlin.

All functions take and return dicts of primitives.
Chaquopy auto-converts Python dicts to Java-accessible objects.

IMPORTANT: All heavy imports (pyXSteam, calculators) are done lazily
inside each function to avoid recursion errors on Python 3.14/Android.
"""

import sys


def _get_steam_properties():
    """Lazy import of steam_properties to avoid load-time recursion."""
    if 'steam_properties' not in sys.modules:
        import steam_properties
    return sys.modules['steam_properties']


def _get_required_spray_calculator():
    if 'required_spray_calculator' not in sys.modules:
        import required_spray_calculator
    return sys.modules['required_spray_calculator']


def _get_spray_impact_calculator():
    if 'spray_impact_calculator' not in sys.modules:
        import spray_impact_calculator
    return sys.modules['spray_impact_calculator']


def _get_transient_simulation_runner():
    if 'transient_simulation_runner' not in sys.modules:
        import transient_simulation_runner
    return sys.modules['transient_simulation_runner']


def calculate_required_spray(
    steam_flow_th, steam_pressure_bar, steam_temp_c,
    target_temp_c, spray_temp_c, initial_metal_temp_c
):
    """Mode A — solve for required spray flow given target temperature."""
    mod = _get_required_spray_calculator()
    return mod.calculate({
        "steam_flow_th": float(steam_flow_th),
        "steam_pressure_bar": float(steam_pressure_bar),
        "steam_temp_c": float(steam_temp_c),
        "target_temp_c": float(target_temp_c),
        "spray_temp_c": float(spray_temp_c),
        "initial_metal_temp_c": float(initial_metal_temp_c),
    })


def calculate_spray_impact(
    steam_flow_th, steam_pressure_bar, steam_temp_c,
    spray_flow_th, spray_temp_c, initial_metal_temp_c
):
    """Mode B — forward: given spray flow, compute resulting temperature."""
    mod = _get_spray_impact_calculator()
    return mod.calculate({
        "steam_flow_th": float(steam_flow_th),
        "steam_pressure_bar": float(steam_pressure_bar),
        "steam_temp_c": float(steam_temp_c),
        "spray_flow_th": float(spray_flow_th),
        "spray_temp_c": float(spray_temp_c),
        "initial_metal_temp_c": float(initial_metal_temp_c),
    })


def run_transient_simulation(
    steam_flow_th, steam_pressure_bar, steam_temp_c,
    target_temp_c, spray_temp_c, initial_metal_temp_c,
    platen_metal_mass_kg, metal_cp,
    burner_heat_mw, num_burners, eta,
    time_step_s, duration_s
):
    """Run the transient burner-ignition simulation."""
    mod = _get_transient_simulation_runner()
    return mod.simulate({
        "steam_flow_th": float(steam_flow_th),
        "steam_pressure_bar": float(steam_pressure_bar),
        "steam_temp_c": float(steam_temp_c),
        "target_temp_c": float(target_temp_c),
        "spray_temp_c": float(spray_temp_c),
        "initial_metal_temp_c": float(initial_metal_temp_c),
        "platen_metal_mass_kg": float(platen_metal_mass_kg),
        "metal_cp": float(metal_cp),
        "burner_heat_mw": float(burner_heat_mw),
        "num_burners": int(num_burners),
        "eta": float(eta),
        "time_step_s": float(time_step_s),
        "duration_s": float(duration_s),
    })


def get_steam_properties(pressure_bar, temperature_c):
    """Get enthalpy at given P,T."""
    sp = _get_steam_properties()
    h, err = sp.h_pt(pressure_bar, temperature_c)
    if err:
        return {"value": None, "error": err["message"]}
    return {"value": round(h, 2), "error": None}


def get_saturation_temp(pressure_bar):
    """Get saturation temperature at given pressure."""
    sp = _get_steam_properties()
    t, err = sp.tsat_p(pressure_bar)
    if err:
        return {"value": None, "error": err["message"]}
    return {"value": round(t, 2), "error": None}
