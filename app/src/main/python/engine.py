"""
Chaquopy bridge — entry points called from Kotlin.

All functions take and return dicts of primitives.
Chaquopy auto-converts Python dicts to Java-accessible objects.
"""

import required_spray_calculator
import spray_impact_calculator
import transient_simulation_runner
import energy_balance_report
import steam_properties as sp


def calculate_required_spray(
    steam_flow_th, steam_pressure_bar, steam_temp_c,
    target_temp_c, spray_temp_c, initial_metal_temp_c
):
    """Mode A — solve for required spray flow given target temperature."""
    return required_spray_calculator.calculate({
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
    return spray_impact_calculator.calculate({
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
    return transient_simulation_runner.simulate({
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


def get_energy_balance(input_dict, result_dict):
    """Generate energy balance report from calculation result."""
    return energy_balance_report.generate(input_dict, result_dict)


def get_steam_properties(pressure_bar, temperature_c):
    """Get enthalpy at given P,T. Returns (value, error) as a dict."""
    h, err = sp.h_pt(pressure_bar, temperature_c)
    if err:
        return {"value": None, "error": err["message"]}
    return {"value": round(h, 2), "error": None}


def get_saturation_temp(pressure_bar):
    """Get saturation temperature at given pressure."""
    t, err = sp.tsat_p(pressure_bar)
    if err:
        return {"value": None, "error": err["message"]}
    return {"value": round(t, 2), "error": None}
