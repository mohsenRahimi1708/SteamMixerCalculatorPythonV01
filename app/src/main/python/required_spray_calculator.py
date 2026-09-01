"""
Mode A — Required Spray Calculator (reverse calculation).

Given a target outlet temperature, solve for required spray flow:
    ṁ_w = ṁ_s · (h_s − h_target) / (h_target − h_w)
"""

import steam_properties as sp

THERMAL_SHOCK_THRESHOLD_C = 50.0


def calculate(inputs):
    """
    inputs: dict with keys:
        steam_flow_th, steam_pressure_bar, steam_temp_c,
        target_temp_c, spray_temp_c, initial_metal_temp_c
    Returns: dict with status "ok" or "error"
    """
    steam_flow = inputs.get("steam_flow_th", 0)
    pressure = inputs.get("steam_pressure_bar", 0)
    steam_temp = inputs.get("steam_temp_c", 0)
    target_temp = inputs.get("target_temp_c", 0)
    spray_temp = inputs.get("spray_temp_c", 0)
    metal_temp = inputs.get("initial_metal_temp_c", 0)
    warnings = []

    # ── Validation ─────────────────────────────────────────────────────
    if steam_flow <= 0:
        return {"status": "error", "message": f"Steam flow must be positive (got {steam_flow})"}
    if target_temp > steam_temp:
        return {"status": "error", "message": f"Target temp ({target_temp} °C) must be ≤ steam temp ({steam_temp} °C)"}

    # ── Enthalpy lookups ──────────────────────────────────────────────
    h_steam, err = sp.h_pt(pressure, steam_temp)
    if err:
        return err

    h_target, err = sp.h_pt(pressure, target_temp)
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

    # ── Energy balance ────────────────────────────────────────────────
    denominator = h_target - h_spray
    if denominator <= 0:
        return {"status": "error", "message": "Spray enthalpy ≥ target enthalpy — cooling not possible with these conditions"}

    spray_flow = steam_flow * (h_steam - h_target) / denominator

    if spray_flow <= 0:
        warnings.append("No spray needed — target temperature equals or exceeds steam inlet temperature.")
        spray_flow = 0.0

    # ── Wet steam warning ─────────────────────────────────────────────
    if spray_flow > 0:
        total_flow = steam_flow + spray_flow
        h_out = (steam_flow * h_steam + spray_flow * h_spray) / total_flow
        h_at_tsat, err = sp.h_pt(pressure, tsat + 0.01)
        if not err and h_out < h_at_tsat:
            warnings.append(f"Outlet enthalpy below saturation at {pressure} bar (T_sat ≈ {tsat:.1f} °C) — wet steam / over-spray")

    # ── Thermal shock advisory (Section 4) ────────────────────────────
    metal_gap = steam_temp - metal_temp
    if metal_gap > THERMAL_SHOCK_THRESHOLD_C:
        warnings.append(
            f"Steam temperature significantly exceeds current platen metal temperature "
            f"(ΔT = {metal_gap:.1f} °C > {THERMAL_SHOCK_THRESHOLD_C:.0f} °C threshold) — "
            f"expect a real response lag beyond this steady-state estimate; consider the transient model instead."
        )

    combined_flow = steam_flow + spray_flow
    temp_drop = steam_temp - target_temp

    return {
        "status": "ok",
        "mode": "A",
        "required_spray_flow_th": round(spray_flow, 4),
        "temperature_drop_c": round(temp_drop, 2),
        "outlet_temp_c": target_temp,
        "combined_flow_th": round(combined_flow, 2),
        "h_steam": round(h_steam, 2),
        "h_target": round(h_target, 2),
        "h_spray": round(h_spray, 2),
        "assumptions": {
            "mode": "A — Required Spray",
            "steam_flow_th": steam_flow,
            "steam_pressure_bar": pressure,
            "steam_temp_c": steam_temp,
            "target_temp_c": target_temp,
            "spray_temp_c": spray_temp,
            "initial_metal_temp_c": metal_temp,
        },
        "warnings": warnings,
    }
