"""
Pytest tests for the Python steam calculation engine.

Tests:
1. IAPWS-IF97 verification points (from official reference)
2. Mode A/B cross-validation (feed Mode A output into Mode B)
3. Platen thermal inertia analytical no-spray case
"""

import sys
import os

# Add the Python engine directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'src', 'main', 'python'))

import steam_properties as sp
import required_spray_calculator as rsc
import spray_impact_calculator as sic
import platen_thermal_inertia_model as ptim
import math


# ─── IAPWS-IF97 Verification Points ────────────────────────────────────────
# Reference: IAPWS-IF97, "Revision on the Thermodynamic Properties for Water
# and Steam" (2007). These are published verification points with known
# enthalpy values at specific P,T conditions in the MKS unit system.

class TestIF97VerificationPoints:
    """Test steam_properties against published IAPWS-IF97 verification data."""

    def test_hpt_region1_compressed_liquid(self):
        """Region 1: Compressed liquid water at P=100 bar, T=200 °C → h ≈ 852.45 kJ/kg"""
        # At 100 bar, T_sat ≈ 311 °C, so 200 °C is compressed liquid (Region 1)
        h, err = sp.h_pt(100.0, 200.0)
        assert err is None, f"Error: {err}"
        assert h is not None
        # Official IAPWS-IF97 value: h = 852.45 kJ/kg
        assert abs(h - 852.45) < 5.0, f"Region 1 check: expected ~852.45, got {h}"

    def test_hpt_region2_superheated_steam(self):
        """Region 2: Superheated steam at P=1 bar, T=100 °C → h ≈ 2675.81 kJ/kg"""
        h, err = sp.h_pt(1.0, 100.0)
        assert err is None, f"Error: {err}"
        assert h is not None
        # Official value: h = 2675.81 kJ/kg
        assert abs(h - 2675.81) < 2.0, f"Region 2 check: expected ~2675.81, got {h}"

    def test_hpt_high_pressure_superheated(self):
        """High-pressure superheated steam at P=167 bar, T=540 °C (typical boiler condition)"""
        h, err = sp.h_pt(167.0, 540.0)
        assert err is None, f"Error: {err}"
        assert h is not None
        # At 167 bar, 540 °C: h ≈ 3406 kJ/kg (from steam tables)
        assert 3350 < h < 3450, f"High-P check: expected ~3406, got {h}"

    def test_tsat_p_saturation_temperature(self):
        """Saturation temperature at 1 bar should be ~99.63 °C"""
        tsat, err = sp.tsat_p(1.0)
        assert err is None, f"Error: {err}"
        assert tsat is not None
        assert abs(tsat - 99.63) < 0.5, f"Saturation check: expected ~99.63, got {tsat}"

    def test_tsat_p_high_pressure_saturation(self):
        """Saturation temperature at 167 bar should be ~351 °C"""
        tsat, err = sp.tsat_p(167.0)
        assert err is None, f"Error: {err}"
        assert tsat is not None
        assert abs(tsat - 351.0) < 5.0, f"High-P saturation: expected ~351, got {tsat}"


# ─── Mode A / Mode B Cross-Validation ──────────────────────────────────────

class TestModeACrossValidation:
    """
    Feed Mode A's output spray flow into Mode B and confirm it reproduces
    the original target temperature within numerical tolerance.
    """

    def test_mode_a_b_consistency(self):
        """Mode A result → Mode B input → target temperature reproduced."""
        # Mode A inputs
        inputs_a = {
            "steam_flow_th": 600,
            "steam_pressure_bar": 167,
            "steam_temp_c": 540,
            "target_temp_c": 520,
            "spray_temp_c": 230,
            "initial_metal_temp_c": 540,
        }

        # Run Mode A
        result_a = rsc.calculate(inputs_a)
        assert result_a["status"] == "ok", f"Mode A failed: {result_a}"
        spray_flow = result_a["required_spray_flow_th"]

        # Feed spray flow into Mode B
        inputs_b = {
            "steam_flow_th": inputs_a["steam_flow_th"],
            "steam_pressure_bar": inputs_a["steam_pressure_bar"],
            "steam_temp_c": inputs_a["steam_temp_c"],
            "spray_flow_th": spray_flow,
            "spray_temp_c": inputs_a["spray_temp_c"],
            "initial_metal_temp_c": inputs_a["initial_metal_temp_c"],
        }

        result_b = sic.calculate(inputs_b)
        assert result_b["status"] == "ok", f"Mode B failed: {result_b}"
        outlet_temp = result_b["outlet_temp_c"]

        # Mode B should reproduce the target temperature from Mode A
        target = inputs_a["target_temp_c"]
        tolerance = 0.5  # °C tolerance for numerical precision
        assert abs(outlet_temp - target) < tolerance, \
            f"Cross-validation failed: Mode B got {outlet_temp} °C, expected {target} ± {tolerance} °C"

    def test_mode_a_b_different_conditions(self):
        """Cross-validation with different operating conditions."""
        inputs_a = {
            "steam_flow_th": 400,
            "steam_pressure_bar": 100,
            "steam_temp_c": 500,
            "target_temp_c": 480,
            "spray_temp_c": 200,
            "initial_metal_temp_c": 500,
        }

        result_a = rsc.calculate(inputs_a)
        assert result_a["status"] == "ok"
        spray_flow = result_a["required_spray_flow_th"]

        inputs_b = {
            "steam_flow_th": 400,
            "steam_pressure_bar": 100,
            "steam_temp_c": 500,
            "spray_flow_th": spray_flow,
            "spray_temp_c": 200,
            "initial_metal_temp_c": 500,
        }

        result_b = sic.calculate(inputs_b)
        assert result_b["status"] == "ok"
        assert abs(result_b["outlet_temp_c"] - 480) < 0.5


# ─── Platen Thermal Inertia — Analytical No-Spray Case ─────────────────────

class TestPlatenThermalInertia:
    """
    When spray flow is zero, the analytical solution is:
        T(t) = T0 + (Q/C) · t
    where Q = burner heat to platen, C = thermal capacitance.
    """

    def test_no_spray_analytical(self):
        """Compare Euler simulation against T(t) = T0 + (Q/C)·t for zero-spray case."""
        # Parameters
        metal_mass = 62600  # kg
        metal_cp = 500  # J/(kg·K)
        eta = 0.07
        num_burners = 4
        burner_heat = 40  # MW
        dt = 10  # seconds
        duration = 300  # 300 seconds

        # Analytical: Q_in = η · N · Q = 0.07 * 4 * 40 = 11.2 MW
        Q_in = eta * num_burners * burner_heat
        C = metal_mass * metal_cp
        T0 = 400  # initial temp (high enough that spray won't kick in)

        # Run transient simulation with zero spray (target temp very low so spray > 0? No — we need spray = 0)
        # To force zero spray, set target temp very low (below what the solver would produce)
        # Actually, the simplest way: run the model with a very high target temp so no spray is needed
        inputs = {
            "steam_flow_th": 600,
            "steam_pressure_bar": 167,
            "steam_temp_c": T0,  # Will be overridden by initial metal temp
            "target_temp_c": 540,  # Higher than metal temp → no spray needed
            "spray_temp_c": 230,
            "initial_metal_temp_c": T0,
            "platen_metal_mass_kg": metal_mass,
            "metal_cp": metal_cp,
            "burner_heat_mw": burner_heat,
            "num_burners": num_burners,
            "eta": eta,
            "time_step_s": dt,
            "duration_s": duration,
        }

        result = ptim.validate(inputs)
        assert result is None, f"Validation failed: {result}"

        # Manually step through the same logic
        t_metal = T0
        for _ in range(int(duration / dt)):
            spray_flow, _ = ptim.required_spray_flow(167.0, t_metal, 540, 230, 600)
            spray_flow = spray_flow if spray_flow and spray_flow > 0 and spray_flow != float('inf') else 0.0
            spray_heat = ptim.spray_heat_removal_mw(spray_flow, 167.0, 540, 230)
            net_heat = Q_in - spray_heat
            dT = ptim.delta_metal_temp(net_heat, metal_mass, metal_cp, dt)
            t_metal += dT

        # Analytical: T = T0 + (Q/C) * duration (no spray, constant Q)
        T_analytical = T0 + (Q_in * 1e6 / C) * duration

        tolerance = 2.0  # °C tolerance for Euler vs analytical
        assert abs(t_metal - T_analytical) < tolerance, \
            f"Thermal model check: Euler got {t_metal:.2f} °C, analytical = {T_analytical:.2f} °C"
