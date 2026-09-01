"""
Platen superheater metal thermal inertia model.

C_metal = M_metal · Cp_metal
dT_metal/dt = Q_net / (M_metal · Cp_metal)

Q_net = Q_burner_to_platen − Q_removed_by_spray
Q_burner_to_platen = η · N_burners · Q_per_burner
"""

import steam_properties as sp


def validate(inputs):
    """Validate transient input parameters. Returns None (ok) or error dict."""
    if inputs.get("steam_flow_th", 0) <= 0:
        return {"status": "error", "message": "Steam flow must be positive"}
    if inputs.get("steam_pressure_bar", 0) < 0.006:
        return {"status": "error", "message": "Pressure must be positive"}
    if inputs.get("platen_metal_mass_kg", 0) <= 0:
        return {"status": "error", "message": "Metal mass must be positive"}
    if inputs.get("metal_cp", 0) <= 0:
        return {"status": "error", "message": "Metal Cp must be positive"}
    if inputs.get("burner_heat_mw", 0) <= 0:
        return {"status": "error", "message": "Burner heat must be positive"}
    if inputs.get("num_burners", 0) <= 0:
        return {"status": "error", "message": "Number of burners must be positive"}
    eta = inputs.get("eta", 0)
    if eta < 0 or eta > 1:
        return {"status": "error", "message": f"Eta must be 0–1 (got {eta})"}
    if inputs.get("time_step_s", 0) <= 0:
        return {"status": "error", "message": "Time step must be positive"}
    if inputs.get("duration_s", 0) <= 0:
        return {"status": "error", "message": "Duration must be positive"}
    return None


def thermal_capacitance(metal_mass_kg, metal_cp):
    """Thermal capacitance in J/K."""
    return metal_mass_kg * metal_cp


def total_burner_heat_mw(eta, num_burners, burner_heat_mw):
    """Total burner heat to platen in MW."""
    return eta * num_burners * burner_heat_mw


def required_spray_flow(pressure_bar, current_metal_temp_c, target_temp_c, spray_temp_c, steam_flow_th):
    """Required spray flow (t/h) to maintain target outlet given current metal temp."""
    h_in, err = sp.h_pt(pressure_bar, current_metal_temp_c)
    if err:
        return None, err
    h_out, err = sp.h_pt(pressure_bar, target_temp_c)
    if err:
        return None, err
    h_spray, err = sp.h_pt(pressure_bar, spray_temp_c)
    if err:
        return None, err

    denom = h_out - h_spray
    if denom <= 0:
        return float('inf'), None

    flow = steam_flow_th * (h_in - h_out) / denom
    return flow, None


def spray_heat_removal_mw(spray_flow_th, pressure_bar, target_temp_c, spray_temp_c):
    """Heat removed by spray in MW."""
    if spray_flow_th <= 0:
        return 0.0
    h_out, _ = sp.h_pt(pressure_bar, target_temp_c)
    h_spray, _ = sp.h_pt(pressure_bar, spray_temp_c)
    if h_out is None or h_spray is None:
        return 0.0
    return spray_flow_th * (h_out - h_spray) / 3600.0


def delta_metal_temp(net_heat_mw, metal_mass_kg, metal_cp, dt_s):
    """Temperature change for one time step (°C)."""
    tc = thermal_capacitance(metal_mass_kg, metal_cp)
    return net_heat_mw * 1e6 * dt_s / tc
