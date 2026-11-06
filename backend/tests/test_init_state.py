"""Initial-condition mode tests: temperature, heat_flux, previous_run."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.init_state import build_initial_state, consistency_residual
from app.thermo.platen_transient import solve_transient

BASE = {
    "m_main_tph": 1000.0,
    "T_main_C": 540.0,
    "P_bar": 167.0,
    "m_spray_tph": 0.0,
    "T_LT_out_C": 490.0,
}


def test_temperature_mode_back_solves_heat_input():
    """Given T_metal, the heat input reproduces the same metal temperature."""
    state = build_initial_state("temperature", BASE, t_metal_init_c=580.0)
    assert state["T_metal_C"] == pytest.approx(580.0)
    assert state["Q_platen_MW"] > 0
    assert consistency_residual(state) < 0.01


def test_heat_flux_mode_back_solves_metal_temperature():
    """Given Q, the metal temperature reproduces the same heat input."""
    state = build_initial_state("heat_flux", BASE, q_platen_init_mw=150.0)
    assert state["Q_platen_MW"] == pytest.approx(150.0)
    assert state["T_metal_C"] > state["T_mean_steam_C"]
    assert consistency_residual(state) < 0.01


def test_modes_are_mutually_consistent():
    """temperature(Q(heat_flux(T))) returns the original metal temperature."""
    q_state = build_initial_state("heat_flux", BASE, q_platen_init_mw=120.0)
    t_state = build_initial_state("temperature", BASE, t_metal_init_c=q_state["T_metal_C"])
    assert t_state["Q_platen_MW"] == pytest.approx(q_state["Q_platen_MW"], rel=1e-2)
    assert consistency_residual(t_state) < 0.01


def test_previous_run_mode_restores_the_stored_state():
    """The stored run state is restored and re-balanced."""
    previous = {"T_metal_C": 570.0, "Q_platen_MW": 60.0, "m_tph": 1000.0, "T_in_C": 490.0}
    state = build_initial_state("previous_run", BASE, previous_run=previous)
    assert state["T_metal_C"] == pytest.approx(570.0)
    assert state["stored_Q_platen_MW"] == pytest.approx(60.0)
    assert state["Q_platen_MW"] > 0
    assert consistency_residual(state) < 0.01


def test_inconsistent_states_are_rejected():
    """Metal colder than steam, or negative heat input, must answer 422."""
    with pytest.raises(DomainError) as exc:
        build_initial_state("temperature", BASE, t_metal_init_c=300.0)
    assert exc.value.status_code == 422
    with pytest.raises(DomainError):
        build_initial_state("heat_flux", BASE, q_platen_init_mw=-10.0)


def test_missing_mode_fields_are_reported():
    """Each mode requires its own field."""
    with pytest.raises(DomainError):
        build_initial_state("temperature", BASE)
    with pytest.raises(DomainError):
        build_initial_state("heat_flux", BASE)
    with pytest.raises(DomainError):
        build_initial_state("previous_run", BASE)


def test_transient_consistency_after_full_run():
    """Feeding the resulting (T_metal, Q_gas) back keeps dT/dt below 0.01 degC/s."""
    state = build_initial_state("temperature", BASE, t_metal_init_c=560.0)
    result = solve_transient(
        m_main_tph=BASE["m_main_tph"],
        t_main_c=BASE["T_main_C"],
        p_bar=BASE["P_bar"],
        m_spray_tph=BASE["m_spray_tph"],
        t_lt_out_c=BASE["T_LT_out_C"],
        geometry=DEFAULT_GEOMETRY,
        dt_s=2.0,
        duration_s=30.0,
        initial_state=state,
    )
    assert abs(result["initial_dTdt_C_per_s"]) < 0.01
