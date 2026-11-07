"""Single-node transient model tests."""

from __future__ import annotations

import math

import pytest

from app.core.errors import DomainError
from app.thermo import burner as burner_mod
from app.thermo.geometry import DEFAULT_GEOMETRY
from app.thermo.init_state import build_initial_state
from app.thermo.platen_transient import solve_transient

BASE = {
    "m_main_tph": 1000.0,
    "T_main_C": 540.0,
    "P_bar": 167.0,
    "m_spray_tph": 0.0,
    "T_LT_out_C": 490.0,
}
#: solver keyword arguments (snake_case) built from the API-style BASE dict
RUN = {
    "m_main_tph": BASE["m_main_tph"],
    "t_main_c": BASE["T_main_C"],
    "p_bar": BASE["P_bar"],
    "m_spray_tph": BASE["m_spray_tph"],
    "t_lt_out_c": BASE["T_LT_out_C"],
}


def _initial(t_metal: float = 560.0) -> dict:
    return build_initial_state("temperature", BASE, t_metal_init_c=t_metal)


def test_initial_state_balance_gives_zero_drift():
    """Mode 'temperature' must produce a state that is already in balance."""
    initial = _initial(560.0)
    assert initial["initial_dTdt_C_per_s"] == pytest.approx(0.0, abs=1e-9)
    assert initial["Q_platen_MW"] > 0


def test_transient_with_balanced_heat_input_holds_metal_temperature():
    """Feeding the back-solved heat input keeps the node steady for a minute."""
    initial = _initial(560.0)
    result = solve_transient(
        **RUN,
        geometry=DEFAULT_GEOMETRY,
        dt_s=2.0,
        duration_s=60.0,
        initial_state=initial,
        q_gas_of_t=None,
    )
    assert abs(result["T_metal_C"][-1] - result["T_metal_C"][0]) < 1.0
    assert abs(result["initial_dTdt_C_per_s"]) < 0.01


def test_energy_conservation_of_the_metal_node():
    """C*dT_m must equal the integrated (Q_gas + Q_conv) with 1 % accuracy."""
    initial = build_initial_state("heat_flux", BASE, q_platen_init_mw=0.1)
    q_gas = lambda t: 5.0 + 0.2 * t  # noqa: E731
    result = solve_transient(
        **RUN,
        geometry=DEFAULT_GEOMETRY,
        dt_s=1.0,
        duration_s=120.0,
        initial_state=initial,
        q_gas_of_t=q_gas,
    )
    net_mw = [g + c for g, c in zip(result["Q_gas_MW"], result["Q_conv_MW"])]
    integral = 0.0
    for index in range(1, len(net_mw)):
        integral += 0.5 * (net_mw[index] + net_mw[index - 1]) * result["dt_s"]
    stored = (
        DEFAULT_GEOMETRY.metal_capacity_j_k
        * (result["T_metal_C"][-1] - result["T_metal_C"][0])
        / 1e6
    )
    assert stored == pytest.approx(integral, rel=1e-2)


def test_explicit_euler_stays_stable_without_substepping():
    """A coarse output step is internally sub-stepped instead of diverging."""
    initial = _initial(600.0)
    result = solve_transient(
        **RUN, geometry=DEFAULT_GEOMETRY, dt_s=30.0, duration_s=600.0, initial_state=initial
    )
    assert math.isfinite(result["T_metal_C"][-1])
    assert result["substeps_max"] > 1
    assert any("sub-stepping" in warning for warning in result["warnings"])


def test_series_are_aligned_and_units_are_physical():
    """Every series has the same length and physical ranges."""
    initial = _initial(560.0)
    result = solve_transient(
        **RUN, geometry=DEFAULT_GEOMETRY, dt_s=2.0, duration_s=100.0, initial_state=initial
    )
    lengths = {len(result[key]) for key in ("time_s", "T_out_C", "T_metal_C", "h_W_m2K", "regime")}
    assert len(lengths) == 1
    assert result["time_s"][-1] == pytest.approx(100.0)
    assert all(t > 300.0 for t in result["T_out_C"])
    assert all(2000.0 < h < 8000.0 for h in result["h_W_m2K"])


def test_settling_times_are_ordered():
    """tau_eff, t63 and t95 must be positive and t63 <= t95."""
    initial = build_initial_state("heat_flux", BASE, q_platen_init_mw=0.1)
    result = solve_transient(
        **RUN,
        geometry=DEFAULT_GEOMETRY,
        dt_s=2.0,
        duration_s=400.0,
        initial_state=initial,
        q_gas_of_t=lambda t: 24.0,
    )
    assert result["tau_s"] > 0
    assert result["t63_s"] is not None and result["t95_s"] is not None
    assert 0 <= result["t63_s"] <= result["t95_s"]


def test_n_nodes_other_than_one_is_rejected_with_a_clear_error():
    """Phase 2 architecture: N > 1 is validated, not silently ignored."""
    with pytest.raises(DomainError) as exc:
        solve_transient(
            **RUN,
            geometry=DEFAULT_GEOMETRY,
            dt_s=2.0,
            duration_s=10.0,
            initial_state=_initial(),
            n_nodes=5,
        )
    assert exc.value.code == "n_nodes_unsupported"


def test_invalid_time_step_is_rejected():
    """A time step larger than the duration is a client error."""
    with pytest.raises(DomainError):
        solve_transient(
            **RUN,
            geometry=DEFAULT_GEOMETRY,
            dt_s=500.0,
            duration_s=60.0,
            initial_state=_initial(),
        )


def test_four_burners_ignition_raises_outlet_to_a_plateau():
    """Acceptance: igniting 4 burners at t = 0 gives a monotonic rise and plateau."""
    initial = build_initial_state("heat_flux", BASE, q_platen_init_mw=0.001)
    schedule = burner_mod.as_schedule(burner_mod.preset_schedule("four_burners"))
    q_gas = burner_mod.q_gas_to_platen_of_t(schedule, q_fraction=0.15, lag_s=5.0)
    result = solve_transient(
        **RUN,
        geometry=DEFAULT_GEOMETRY,
        dt_s=2.0,
        duration_s=900.0,
        initial_state=initial,
        q_gas_of_t=q_gas,
    )
    # the 5 s gas transport lag causes a sub-millidegree dip before the burners bite
    settled = [round(value, 6) for value, t in zip(result["T_out_C"], result["time_s"]) if t >= 10.0]
    assert all(later >= earlier - 1e-3 for earlier, later in zip(settled, settled[1:]))
    assert result["T_out_C"][-1] > result["T_out_C"][0] + 5.0
    assert result["t95_s"] is not None
    # plateau: the last 100 s move the outlet by less than 1 degC
    tail = result["T_out_C"][-51:]
    assert max(tail) - min(tail) < 1.0
