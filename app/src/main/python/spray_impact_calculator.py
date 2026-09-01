"""
Mode B — Spray Impact Calculator (forward calculation).

Given a spray flow, calculate the resulting outlet temperature:
    h_out = (ṁ_s · h_s + ṁ_w · h_w) / (ṁ_s + ṁ_w)
    T_out = t_ph(P, h_out)
    ΔT = T_steam − T_out
"""

import steam_properties as sp

THERMAL_SHOCK_THRESHOLD_C = 50.0


def calculate(inputs):
    """
    inputs: dict with keys:
        steam_flow_th, steam_pressure_bar, steam_temp_c,
        spray_flow_th, spray_temp_c, initial_metal_temp_c
    Returns: dict with status "ok" or "error"
    """
    steam_flow = inputs.get("steam_flow_th", 0)
    pressure = inputs.get("steam_pressure_bar", 0)
    steam_temp = inputs.get("steam_temp_c", 0)
    spray_flow = inputs.get("spray_flow_th", 0)
    spray_temp = inputs.get("spray_temp_c", 0)
    metal_temp = inputs.get("initial_metal_temp_c", 0)
    warnings = []

    # ── Validation ─────────────────────────────────────────────────────
    if steam_flow <= 0:
        return {"status": "error", "message": f"Steam flow must be positive (got {steam_flow})"}
    if spray_flow < 0:
        return {"status": "error", "message": f"Spray flow must be non-negative (got {spray_flow})"}
    if spray_flow > steam_flow * 2:
        return {"status": "error", "message": f"Spray flow ({spray_flow} t/h) exceeds 2× steam flow — likely input error"}

    # ── Enthalpy lookups ──────────────────────────────────────────────
    h_steam, err = sp.h_pt(pressure, steam_temp)
    if err:
        return err

    h_spray, err = sp.h_pt(pressure, spray_temp)
    if err:
        return err

    # ── Saturation check ──────────────────────────────────────────────
    tsat, err = sp.tsat_p(pressure)
    if err:
        return err

    if spray_temp >= tsat:
        return {"status": "error", "message": f"Spray water ({spray_temp} °C) exceeds saturation ({tsat:.1f} °C) — must be subcooled liquid"}

    # ── Zero spray case ───────────────────────────────────────────────
    if spray_flow <= 0:
        warnings.append("Zero spray flow — outlet temperature equals steam inlet temperature.")
        return {
            "status": "ok",
            "mode": "B",
            "outlet_temp_c": steam_temp,
            "temperature_drop_c": 0.0,
            "h_out": round(h_steam, 2),
            "combined_flow_th": steam_flow,
            "h_steam": round(h_steam, 2),
            "h_spray": round(h_spray, 2),
            "assumptions": {
                "mode": "B — Spray Impact (Forward)",
                "steam_flow_th": steam_flow,
                "steam_pressure_bar": pressure,
                "steam_temp_c": steam_temp,
                "spray_flow_th": spray_flow,
                "spray_temp_c": spray_temp,
                "initial_metal_temp_c": metal_temp,
            },
            "warnings": warnings,
        }

    # ── Forward energy balance ────────────────────────────────────────
    combined_flow = steam_flow + spray_flow
    h_out = (steam_flow * h_steam + spray_flow * h_spray) / combined_flow

    # Backward equation: T_out = t_ph(P, h_out)
    t_out, err = sp.t_ph(pressure, h_out)
    if err:
        return err

    delta_t = steam_temp - t_out

    # ── Wet steam warning ─────────────────────────────────────────────
    if t_out <= tsat:
        warnings.append(
            f"Outlet temperature ({t_out:.1f} °C) falls below saturation temperature "
            f"({tsat:.1f} °C at {pressure} bar) — wet steam / full quenching, outside model's valid output range."
        )

    # ── Thermal shock advisory (Section 4) ────────────────────────────
    metal_gap = steam_temp - metal_temp
    if metal_gap > THERMAL_SHOCK_THRESHOLD_C:
        warnings.append(
            f"Steam temperature significantly exceeds current platen metal temperature "
            f"(ΔT = {metal_gap:.1f} °C > {THERMAL_SHOCK_THRESHOLD_C:.0f} °C threshold) — "
            f"expect a real response lag beyond this steady-state estimate; consider the transient model instead."
        )

    return {
        "status": "ok",
        "mode": "B",
        "outlet_temp_c": round(t_out, 2),
        "temperature_drop_c": round(delta_t, 2),
        "h_out": round(h_out, 2),
        "combined_flow_th": round(combined_flow, 2),
        "h_steam": round(h_steam, 2),
        "h_spray": round(h_spray, 2),
        "assumptions": {
            "mode": "B — Spray Impact (Forward)",
            "steam_flow_th": steam_flow,
            "steam_pressure_bar": pressure,
            "steam_temp_c": steam_temp,
            "spray_flow_th": spray_flow,
            "spray_temp_c": spray_temp,
            "initial_metal_temp_c": metal_temp,
        },
        "warnings": warnings,
    }
