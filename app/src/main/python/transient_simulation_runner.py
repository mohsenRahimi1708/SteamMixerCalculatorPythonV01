"""
Time-stepped transient simulation combining burner heat input,
platen metal thermal inertia, and spray-water demand.

At each step:
1. Q_in = η · N_burners · Q_per_burner
2. Steam leaving platen at metal temperature
3. Required spray to maintain target outlet
4. Q_spray = ṁ_w · (h_out - h_spray)
5. Q_net = Q_in - Q_spray
6. T(t+dt) = T(t) + Q_net · dt / (M · Cp)
"""

import platen_thermal_inertia_model as ptim


def simulate(inputs):
    """
    inputs: dict with all transient simulation parameters.
    Returns: dict with status "ok" or "error", containing steps list.
    """
    err = ptim.validate(inputs)
    if err:
        return err

    steam_flow = inputs["steam_flow_th"]
    pressure = inputs["steam_pressure_bar"]
    target_temp = inputs["target_temp_c"]
    spray_temp = inputs["spray_temp_c"]
    initial_metal = inputs["initial_metal_temp_c"]
    metal_mass = inputs["platen_metal_mass_kg"]
    metal_cp = inputs["metal_cp"]
    burner_heat = inputs["burner_heat_mw"]
    num_burners = inputs["num_burners"]
    eta = inputs["eta"]
    dt = inputs["time_step_s"]
    duration = inputs["duration_s"]

    total_burner = ptim.total_burner_heat_mw(eta, num_burners, burner_heat)
    total_steps = int(duration / dt)
    warnings = []
    steps = []

    t_metal = initial_metal

    for step in range(total_steps + 1):
        time_s = step * dt

        # Required spray flow given current metal temperature
        spray_flow, err = ptim.required_spray_flow(
            pressure, t_metal, target_temp, spray_temp, steam_flow
        )
        if err:
            return err
        spray_flow_actual = spray_flow if spray_flow and spray_flow > 0 and spray_flow != float('inf') else 0.0

        spray_heat = ptim.spray_heat_removal_mw(spray_flow_actual, pressure, target_temp, spray_temp)
        net_heat = total_burner - spray_heat

        steps.append({
            "time_s": round(time_s, 2),
            "metal_temp_c": round(t_metal, 2),
            "spray_flow_th": round(spray_flow_actual, 4),
            "net_heat_mw": round(net_heat, 4),
            "burner_heat_mw": round(total_burner, 4),
            "spray_heat_mw": round(spray_heat, 4),
        })

        # Euler forward update
        if step < total_steps:
            dT = ptim.delta_metal_temp(net_heat, metal_mass, metal_cp, dt)
            t_metal += dT

    # Final steady-state spray
    final_spray, _ = ptim.required_spray_flow(pressure, t_metal, target_temp, spray_temp, steam_flow)
    final_spray_val = final_spray if final_spray and final_spray > 0 and final_spray != float('inf') else 0.0

    if total_burner <= 0:
        warnings.append("No burner heat input — metal temperature will remain constant.")

    return {
        "status": "ok",
        "mode": "transient",
        "steps": steps,
        "final_steady_state_spray_th": round(final_spray_val, 4),
        "final_metal_temp_c": round(t_metal, 2),
        "assumptions": {
            "mode": "Transient Simulation",
            "steam_flow_th": steam_flow,
            "steam_pressure_bar": pressure,
            "steam_temp_c": inputs.get("steam_temp_c", steam_flow),
            "target_temp_c": target_temp,
            "spray_temp_c": spray_temp,
            "initial_metal_temp_c": initial_metal,
            "platen_metal_mass_kg": metal_mass,
            "metal_cp": metal_cp,
            "burner_heat_mw": burner_heat,
            "num_burners": num_burners,
            "eta": eta,
        },
        "warnings": warnings,
    }
