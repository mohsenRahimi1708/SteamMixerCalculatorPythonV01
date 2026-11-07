"""Spray mixing and steady-state platen tests."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.thermo import if97, spray
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.platen_ss import solve_steady

P_BAR = 167.0
T_MAIN = 540.0
M_MAIN = 1000.0


def test_zero_spray_keeps_main_steam_temperature():
    """Without spray the platen inlet equals the main steam temperature."""
    result = spray.mix_spray(M_MAIN, T_MAIN, P_BAR, 0.0)
    assert result["T_platen_in_C"] == pytest.approx(T_MAIN, abs=1e-3)
    assert result["m_total_tph"] == pytest.approx(M_MAIN)


def test_spray_mixing_is_adiabatic():
    """Enthalpy is conserved: m_main*h_main + m_spray*h_spray = m_total*h_mix."""
    result = spray.mix_spray(M_MAIN, T_MAIN, P_BAR, 30.0)
    expected = (M_MAIN * result["h_main_kJ_kg"] + 30.0 * result["h_spray_kJ_kg"]) / 1030.0
    assert result["h_mix_kJ_kg"] == pytest.approx(expected, rel=1e-12)
    assert result["T_platen_in_C"] < T_MAIN


def test_spray_flow_monotonically_cools_the_mix():
    """More spray always lowers the mixed temperature."""
    temps = [spray.mix_spray(M_MAIN, T_MAIN, P_BAR, m)["T_platen_in_C"] for m in (0, 10, 30, 60)]
    assert temps == sorted(temps, reverse=True)


def test_spray_temperature_drop_matches_input():
    """deltaT_spray = T_LT_out - T_platen_in."""
    result = solve_steady(
        M_MAIN, T_MAIN, P_BAR, 30.0, 490.0, 60.0, DEFAULT_GEOMETRY, "gnielinski"
    )
    assert result["deltaT_spray_C"] == pytest.approx(490.0 - result["T_platen_in_C"], abs=1e-9)


def test_steady_outlet_matches_independent_if97_enthalpy_balance():
    """Outlet temperature reproduces the enthalpy balance to within 0.5 degC."""
    result = solve_steady(
        M_MAIN, T_MAIN, P_BAR, 30.0, 490.0, 60.0, DEFAULT_GEOMETRY, "gnielinski"
    )
    mixed = spray.mix_spray(M_MAIN, T_MAIN, P_BAR, 30.0)
    h_out = mixed["h_mix_kJ_kg"] + 60.0 * 3600.0 / mixed["m_total_tph"]
    t_expected = if97.t_ph(P_BAR, h_out)
    assert result["T_platen_out_C"] == pytest.approx(t_expected, abs=0.5)
    assert if97.h_pt(P_BAR, result["T_platen_out_C"]) == pytest.approx(h_out, rel=1e-6)


def test_steady_derived_geometry_matches_published_capacitance():
    """Frozen geometry must reproduce the published 98.1 t / 49.1 MJ/K / 79 s."""
    geometry = DEFAULT_GEOMETRY
    assert geometry.n_tubes == 172
    assert geometry.d_i_m == pytest.approx(0.041)
    assert geometry.internal_volume_m3 == pytest.approx(13.47, abs=0.1)
    assert geometry.metal_mass_kg / 1000.0 == pytest.approx(98.1, abs=0.5)
    assert geometry.metal_capacity_j_k / 1e6 == pytest.approx(49.1, abs=1.0)
    # published 79 s uses cp = 2.3 kJ/(kg*K); IF97 cp at 515 degC is ~2.9, so 60-70 s
    assert 58.0 < geometry.tau_s(1000.0) < 72.0


def test_steady_heat_absorption_increases_outlet_temperature():
    """More absorbed heat means a hotter outlet."""
    temps = [
        solve_steady(M_MAIN, T_MAIN, P_BAR, 0.0, 490.0, q, DEFAULT_GEOMETRY, "gnielinski")[
            "T_platen_out_C"
        ]
        for q in (10.0, 30.0, 60.0, 80.0)
    ]
    assert temps == sorted(temps)


def test_steady_rejects_invalid_inputs():
    """Negative flows and out-of-envelope pressures are client errors."""
    with pytest.raises(DomainError):
        solve_steady(0.0, T_MAIN, P_BAR, 0.0, 490.0, 144.0)
    with pytest.raises(DomainError):
        solve_steady(M_MAIN, T_MAIN, P_BAR, -5.0, 490.0, 144.0)
    with pytest.raises(DomainError):
        solve_steady(M_MAIN, T_MAIN, 500.0, 0.0, 490.0, 144.0)
    with pytest.raises(DomainError):
        solve_steady(M_MAIN, T_MAIN, P_BAR, 0.0, 490.0, -20.0)
