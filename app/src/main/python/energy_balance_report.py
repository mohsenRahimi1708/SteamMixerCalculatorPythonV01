"""
Energy Balance Report generator.

Builds a human-readable energy balance breakdown from calculation results.
"""

import steam_properties as sp


def generate(inputs, calc_result):
    """
    Generate energy balance report.

    inputs: original calculation input dict
    calc_result: result dict from one of the calculators
    Returns: dict with formatted report sections.
    """
    mode = calc_result.get("mode", "?")
    assumptions = calc_result.get("assumptions", {})

    steam_flow = assumptions.get("steam_flow_th", 0)
    pressure = assumptions.get("steam_pressure_bar", 0)
    steam_temp = assumptions.get("steam_temp_c", 0)
    target_temp = assumptions.get("target_temp_c", 0)
    spray_temp = assumptions.get("spray_temp_c", 0)
    metal_temp = assumptions.get("initial_metal_temp_c", 0)

    sections = []

    # ── Input conditions ──────────────────────────────────────────────
    sections.append({
        "title": "INPUT CONDITIONS",
        "lines": [
            ("Steam flow", f"{steam_flow} t/h"),
            ("Steam pressure", f"{pressure} bar"),
            ("Steam inlet temp", f"{steam_temp} °C"),
            ("Spray water temp", f"{spray_temp} °C"),
            ("Initial metal temp", f"{metal_temp} °C"),
        ]
    })

    if mode == "A":
        sections.append({
            "title": "INPUT CONDITIONS (continued)",
            "lines": [
                ("Target outlet", f"{target_temp} °C"),
            ]
        })
    elif mode == "B":
        spray_flow = assumptions.get("spray_flow_th", 0)
        sections.append({
            "title": "INPUT CONDITIONS (continued)",
            "lines": [
                ("Spray flow", f"{spray_flow} t/h"),
            ]
        })

    # ── Steam-side enthalpies ─────────────────────────────────────────
    h_steam = calc_result.get("h_steam", 0)
    h_spray = calc_result.get("h_spray", 0)
    h_out = calc_result.get("h_target", 0) or calc_result.get("h_out", 0)

    sections.append({
        "title": "STEAM-SIDE ENTHALPIES",
        "lines": [
            ("h_steam(P,T_in)", f"{h_steam:.2f} kJ/kg"),
            ("h_spray(P,T_spray)", f"{h_spray:.2f} kJ/kg"),
            ("h_out", f"{h_out:.2f} kJ/kg"),
        ]
    })

    # ── Result ────────────────────────────────────────────────────────
    if mode == "A":
        spray_flow = calc_result.get("required_spray_flow_th", 0)
        temp_drop = calc_result.get("temperature_drop_c", 0)
        dh_steam = h_steam - h_out
        dh_spray = h_out - h_spray
        heat_removed = spray_flow * dh_spray / 3600.0 if dh_spray > 0 else 0

        sections.append({
            "title": "REQUIRED SPRAY CALCULATION",
            "lines": [
                ("Δh (steam→target)", f"{dh_steam:.2f} kJ/kg"),
                ("Δh (target→spray)", f"{dh_spray:.2f} kJ/kg"),
                ("Required spray flow", f"{spray_flow:.4f} t/h"),
                ("Temperature drop", f"{temp_drop:.2f} °C"),
                ("Heat removed by spray", f"{heat_removed:.4f} MW"),
            ]
        })

    elif mode == "B":
        delta_t = calc_result.get("temperature_drop_c", 0)
        combined = calc_result.get("combined_flow_th", 0)
        spray_flow = assumptions.get("spray_flow_th", 0)
        dh_steam = h_steam - h_out
        dh_spray = h_out - h_spray
        heat_removed = spray_flow * dh_spray / 3600.0 if dh_spray > 0 else 0

        sections.append({
            "title": "SPRAY IMPACT CALCULATION",
            "lines": [
                ("Δh (steam→out)", f"{dh_steam:.2f} kJ/kg"),
                ("Δh (out→spray)", f"{dh_spray:.2f} kJ/kg"),
                ("Outlet temperature", f"{calc_result.get('outlet_temp_c', 0):.2f} °C"),
                ("Temperature drop", f"{delta_t:.2f} °C"),
                ("Combined flow", f"{combined:.2f} t/h"),
                ("Heat removed by spray", f"{heat_removed:.4f} MW"),
            ]
        })

    # ── Warnings ──────────────────────────────────────────────────────
    warnings = calc_result.get("warnings", [])
    if warnings:
        sections.append({
            "title": "WARNINGS",
            "lines": [(w, "") for w in warnings]
        })

    return {
        "status": "ok",
        "sections": sections,
        "mode_label": assumptions.get("mode", f"Mode {mode}"),
    }
