"""IAPWS-IF97 verification tests against published reference values."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError, If97RangeError
from app.thermo import if97

# Official IF97 verification table (IAPWS-IF97 release, basic equations).
REGION1_POINTS = [
    # (P_bar, T_C, h_kJ_kg, v_m3_kg, cp_kJ_kgK, s_kJ_kgK)
    (30.0, 26.85, 115.331273, 0.00100215168, 4.17301218, 0.392294792),
    (800.0, 26.85, 184.142828, 0.000971180894, 4.00097563, 0.368563852),
]
REGION2_POINTS = [
    (0.035, 426.85, 3335.68375, 2.57139449, 10.1749996, 8.01970609),
    (300.0, 426.85, 2631.49474, 0.00450160475, 5.17540298, 5.17540298),
]


@pytest.mark.parametrize("p_bar,t_c,h,v,cp,s", REGION1_POINTS)
def test_region1_verification_points(p_bar, t_c, h, v, cp, s):
    """Compressed liquid verification points (region 1)."""
    props = if97.props_pt(p_bar, t_c)
    assert props["region"] == 1
    assert props["h"] == pytest.approx(h, rel=2e-4)
    assert props["v"] == pytest.approx(v, rel=2e-4)


@pytest.mark.parametrize("p_bar,t_c,h,v,cp,s", REGION2_POINTS)
def test_region2_verification_points(p_bar, t_c, h, v, cp, s):
    """Superheated steam verification points (region 2)."""
    props = if97.props_pt(p_bar, t_c)
    assert props["region"] == 2
    assert props["h"] == pytest.approx(h, rel=2e-4)


def test_region2_high_pressure_steam_enthalpy():
    """Design main steam state of the unit: 167 bar, 540 degC."""
    h = if97.h_pt(167.0, 540.0)
    assert 3395.0 < h < 3415.0
    assert if97.region_of(167.0, 540.0) == 2


def test_saturation_temperature_and_pressure():
    """Region 4 saturation equations."""
    assert if97.psat_t(26.85) == pytest.approx(0.0353658941, rel=2e-4)  # bar
    assert if97.tsat_p(1.0) == pytest.approx(99.6059, abs=0.05)
    assert if97.tsat_p(167.0) == pytest.approx(350.84, abs=0.2)


def test_saturated_liquid_enthalpy():
    """Saturated liquid enthalpy at the live steam pressure."""
    h_f = if97.sat_liquid_h(167.0)
    assert 1650.0 < h_f < 1700.0


def test_backward_t_ph_inverts_forward_h_pt():
    """IF97 backward T(P,h) must invert the forward equation to < 1e-3 degC."""
    for p_bar, t_c in ((167.0, 540.0), (167.0, 480.0), (100.0, 400.0), (30.0, 350.0)):
        h = if97.h_pt(p_bar, t_c)
        assert if97.t_ph(p_bar, h) == pytest.approx(t_c, abs=1e-3)


def test_transport_properties_are_physical():
    """Viscosity and conductivity must match the IAPWS transport correlations."""
    props = if97.props_pt(167.0, 540.0)
    assert 2.8e-5 < props["mu"] < 3.4e-5
    assert 0.07 < props["k"] < 0.10
    assert 2.6 < props["cp"] < 3.0
    assert 45.0 < props["rho"] < 55.0


def test_out_of_range_states_are_rejected():
    """Outside the IF97 envelope the API must answer with a domain error."""
    with pytest.raises(If97RangeError):
        if97.h_pt(167.0, 900.0)
    with pytest.raises(DomainError):
        if97.h_pt(5000.0, 500.0)
