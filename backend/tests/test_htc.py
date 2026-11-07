"""Heat transfer coefficient tests.

The Dittus-Boelter check is fully hand-computed from fixed properties so it is
independent of the IF97 library: any regression in the correlation constants is
caught at 1e-12 relative tolerance.
"""

from __future__ import annotations

import math

import pytest

from app.core.errors import DomainError
from app.thermo import htc, if97

# Fixed synthetic properties at 167 bar / 500 degC (rounded for hand calculation).
MU = 3.0e-5  # Pa*s
CP = 2.5  # kJ/(kg*K)
K = 0.07  # W/(m*K)
D_I = 0.041  # m
N_TUBES = 172
M_TOTAL_TPH = 1000.0

PROPS = {"mu": MU, "cp": CP, "k": K}


def _hand_reynolds() -> float:
    m_dot_tube = (M_TOTAL_TPH / 3.6) / N_TUBES
    return 4.0 * m_dot_tube / (math.pi * D_I * MU)


def _hand_prandtl() -> float:
    return MU * CP * 1000.0 / K


def test_reynolds_hand_calculation():
    """Re = 4*m_dot_tube/(pi*d_i*mu) exactly."""
    result = htc.htc_from_props(PROPS, M_TOTAL_TPH, D_I, N_TUBES, "dittus_boelter")
    assert result["Re"] == pytest.approx(_hand_reynolds(), rel=1e-12)


def test_prandtl_hand_calculation():
    """Pr = mu*cp/k with cp converted from kJ to J."""
    result = htc.htc_from_props(PROPS, M_TOTAL_TPH, D_I, N_TUBES, "dittus_boelter")
    assert result["Pr"] == pytest.approx(_hand_prandtl(), rel=1e-12)


def test_dittus_boelter_hand_calculation():
    """Nu, h and the friction factor match the closed-form correlations."""
    result = htc.htc_from_props(PROPS, M_TOTAL_TPH, D_I, N_TUBES, "dittus_boelter")
    re_number = _hand_reynolds()
    pr_number = _hand_prandtl()
    nu_expected = 0.023 * re_number ** 0.8 * pr_number ** 0.4
    h_expected = nu_expected * K / D_I
    assert result["Nu_DB"] == pytest.approx(nu_expected, rel=1e-12)
    assert result["Nu"] == pytest.approx(nu_expected, rel=1e-12)
    assert result["h_W_m2K"] == pytest.approx(h_expected, rel=1e-12)
    f_expected = (0.79 * math.log(re_number) - 1.64) ** -2
    assert result["f"] == pytest.approx(f_expected, rel=1e-12)


def test_gnielinski_hand_calculation():
    """Gnielinski correlation reproduces the textbook expression."""
    result = htc.htc_from_props(PROPS, M_TOTAL_TPH, D_I, N_TUBES, "gnielinski")
    re_number = _hand_reynolds()
    pr_number = _hand_prandtl()
    f = (0.79 * math.log(re_number) - 1.64) ** -2
    expected = (f / 8) * (re_number - 1000) * pr_number / (
        1 + 12.7 * math.sqrt(f / 8) * (pr_number ** (2 / 3) - 1)
    )
    assert result["Nu_Gnielinski"] == pytest.approx(expected, rel=1e-12)
    assert result["Nu"] == pytest.approx(expected, rel=1e-12)


def test_cooling_exponent():
    """Cooling uses Pr^0.3, heating uses Pr^0.4."""
    heating = htc.nusselt_db(50000, 2.0, heating=True)
    cooling = htc.nusselt_db(50000, 2.0, heating=False)
    assert cooling < heating


def test_regime_thresholds():
    """The laminar/transition/turbulent boundaries are exactly at 2300 / 10000."""
    assert htc.regime(2299.9) == "laminar"
    assert htc.regime(2300.0) == "transition"
    assert htc.regime(9999.9) == "transition"
    assert htc.regime(10000.0) == "turbulent"


def test_transition_is_continuous_and_monotonic():
    """Nu must be continuous at both regime boundaries and rise with Re."""
    re_values = [2300.0, 3000.0, 5000.0, 8000.0, 9999.0, 10000.0]
    nus = [htc.nusselt(re_number, 0.95, "gnielinski") for re_number in re_values]
    assert nus[0] == pytest.approx(4.36, rel=1e-9)
    assert nus[-1] == pytest.approx(
        htc.nusselt_gnielinski(10000.0, 0.95), rel=1e-9
    )
    assert all(later > earlier for earlier, later in zip(nus, nus[1:]))


def test_low_flow_forces_laminar_regime():
    """A 10 t/h run through the platen must fall in the laminar band."""
    result = htc.htc(m_tph=1.0, p_bar=167.0, t_c=500.0, d_i_m=D_I, n_tubes=N_TUBES)
    assert result["regime"] == "laminar"
    assert result["Nu"] == pytest.approx(4.36)


def test_design_point_is_turbulent_with_physical_coefficient():
    """At 1000 t/h the platen runs turbulent with h in the engineering range."""
    result = htc.htc(m_tph=1000.0, p_bar=167.0, t_c=500.0, d_i_m=D_I, n_tubes=N_TUBES)
    assert result["regime"] == "turbulent"
    assert result["Re"] > 1e6
    assert 2000.0 < result["h_W_m2K"] < 8000.0


def test_unknown_method_rejected():
    """Unknown correlations are a client error, not a silent fallback."""
    with pytest.raises(DomainError):
        htc.htc(1000.0, 167.0, 500.0, D_I, N_TUBES, method="churchill")


def test_htc_at_if97_state_is_consistent():
    """htc() must use the IF97 viscosity/conductivity it reports."""
    result = htc.htc(1000.0, 167.0, 500.0, D_I, N_TUBES)
    props = if97.props_pt(167.0, 500.0)
    assert result["mu_Pas"] == pytest.approx(props["mu"], rel=1e-12)
    m_dot_tube = (1000.0 / 3.6) / N_TUBES
    assert result["Re"] == pytest.approx(4 * m_dot_tube / (math.pi * D_I * props["mu"]), rel=1e-12)
