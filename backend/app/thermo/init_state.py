"""Initial-condition builder for the single-node platen model.

Three user-selectable modes:

``temperature``   metal temperature is given, the steady heat input that keeps
                  that temperature is back-solved
``heat_flux``     heat input is given, the matching metal temperature is
                  back-solved
``previous_run``  metal state is restored from a stored run and re-balanced

The back-solve is analytic.  For the lumped node at steady state:

    Q_gas = Q_steam = m_dot*cp*(T_out - T_in)
    T_mean = (T_in + T_out)/2
    T_metal = T_mean + Q_gas/(h*A)

so each mode is a short fixed-point iteration on cp and h only, never a search
that can diverge.  In every mode ``T_metal > mean steam temperature`` and
``Q_gas >= 0`` must hold, otherwise the state is physically impossible and the
API answers 422.
"""

from __future__ import annotations

import math

from app.core.errors import DomainError
from app.thermo import if97, spray
from app.thermo.geometry import DEFAULT_GEOMETRY, PlatenGeometry
from app.thermo.platen_ss import implicit_outlet_temperature, steam_to_metal_ntu

INITIAL_MODES = ("temperature", "heat_flux", "previous_run")
T_EVAL_MIN_C = 1.0
T_EVAL_MAX_C = 699.0


def _clamp_eval(t_c: float) -> float:
    """Keep the property evaluation inside the IF97 envelope."""
    return min(max(t_c, T_EVAL_MIN_C), T_EVAL_MAX_C)


def _inlet_state(base: dict) -> dict:
    """Mixed platen inlet state shared by every mode."""
    return spray.mix_spray(
        m_main_tph=base["m_main_tph"],
        t_main_c=base["T_main_C"],
        p_bar=base["P_bar"],
        m_spray_tph=base["m_spray_tph"],
        t_lt_out_c=base.get("T_LT_out_C"),
    )


def _mcp_mw_per_k(m_total_tph: float, p_bar: float, t_c: float) -> float:
    """Steam heat capacity rate m_dot*cp [MW/K] at a state point."""
    cp_kj_kgk = float(if97.props_pt(p_bar, _clamp_eval(t_c))["cp"])
    return (m_total_tph / 3.6) * cp_kj_kgk / 1000.0


def _steady_from_metal(
    t_in_c: float,
    t_metal_c: float,
    m_total_tph: float,
    p_bar: float,
    geometry: PlatenGeometry,
    htc_method: str,
) -> dict:
    """Steady node state for a given metal temperature (returns Q and T_out)."""
    mean = 0.5 * (t_in_c + t_metal_c)
    diag: dict = {}
    ntu = 0.0
    t_out = t_in_c
    for _ in range(8):
        ntu, diag = steam_to_metal_ntu(
            m_total_tph, p_bar, _clamp_eval(mean), geometry, htc_method
        )
        t_out = implicit_outlet_temperature(t_in_c, t_metal_c, ntu)
        new_mean = 0.5 * (t_in_c + t_out)
        if abs(new_mean - mean) < 1e-10:
            mean = new_mean
            break
        mean = new_mean
    mcp = _mcp_mw_per_k(m_total_tph, p_bar, mean)
    q_gas_mw = mcp * (t_out - t_in_c)
    return {
        "T_out_C": t_out,
        "T_mean_steam_C": 0.5 * (t_in_c + t_out),
        "Q_platen_MW": q_gas_mw,
        "NTU": ntu,
        "diag": diag,
        "mcp_MW_K": mcp,
    }


def _steady_from_heat(
    q_gas_mw: float,
    t_in_c: float,
    m_total_tph: float,
    p_bar: float,
    geometry: PlatenGeometry,
    htc_method: str,
) -> dict:
    """Steady node state for a given heat input (returns T_metal and T_out)."""
    mcp = _mcp_mw_per_k(m_total_tph, p_bar, t_in_c)
    t_out = t_in_c + (q_gas_mw / mcp if mcp > 0 else 0.0)
    diag: dict = {}
    ntu = 0.0
    for _ in range(8):
        mean = 0.5 * (t_in_c + t_out)
        mcp = _mcp_mw_per_k(m_total_tph, p_bar, mean)
        t_out_new = t_in_c + (q_gas_mw / mcp if mcp > 0 else 0.0)
        ntu, diag = steam_to_metal_ntu(
            m_total_tph, p_bar, _clamp_eval(0.5 * (t_in_c + t_out_new)), geometry, htc_method
        )
        if abs(t_out_new - t_out) < 1e-10:
            t_out = t_out_new
            break
        t_out = t_out_new
    mean = 0.5 * (t_in_c + t_out)
    conductance = diag["h_W_m2K"] * geometry.inner_area_m2
    t_metal = mean + (q_gas_mw * 1e6 / conductance if conductance > 0 else math.inf)
    return {
        "T_out_C": t_out,
        "T_mean_steam_C": mean,
        "T_metal_C": t_metal,
        "Q_platen_MW": q_gas_mw,
        "NTU": ntu,
        "diag": diag,
        "mcp_MW_K": mcp,
    }


def build_initial_state(
    mode: str,
    base: dict,
    t_metal_init_c: float | None = None,
    q_platen_init_mw: float | None = None,
    previous_run: dict | None = None,
    geometry: PlatenGeometry = DEFAULT_GEOMETRY,
    htc_method: str = "gnielinski",
    heating: bool = True,
) -> dict:
    """Build and validate the N = 1 initial state.

    ``base`` carries m_main_tph, T_main_C, P_bar, m_spray_tph and T_LT_out_C.
    """
    if mode not in INITIAL_MODES:
        raise DomainError(
            "out_of_envelope",
            "Unknown initial-condition mode.",
            "\u062d\u0627\u0644\u062a \u0634\u0631\u0627\u06cc\u0637 \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0646\u0627\u0634\u0646\u0627\u062e\u062a\u0647 \u0627\u0633\u062a.",
            context={"initial_mode": mode},
        )
    mixed = _inlet_state(base)
    t_in = mixed["T_platen_in_C"]
    m_total = mixed["m_total_tph"]
    p_bar = base["P_bar"]
    stored_q: float | None = None
    warnings: list[str] = []

    if mode == "temperature":
        if t_metal_init_c is None:
            raise DomainError(
                "out_of_envelope",
                "T_metal_init_C is required for the temperature initial mode.",
                "\u062f\u0631 \u062d\u0627\u0644\u062a \u062f\u0645\u0627\u06cc\u06cc\u060c \u062f\u0645\u0627\u06cc \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0641\u0644\u0632 \u0644\u0627\u0632\u0645 \u0627\u0633\u062a.",
            )
        t_metal = float(t_metal_init_c)
        steady = _steady_from_metal(t_in, t_metal, m_total, p_bar, geometry, htc_method)
    elif mode == "heat_flux":
        if q_platen_init_mw is None:
            raise DomainError(
                "out_of_envelope",
                "Q_platen_init_MW is required for the heat_flux initial mode.",
                "\u062f\u0631 \u062d\u0627\u0644\u062a \u0634\u0627\u0631 \u062d\u0631\u0627\u0631\u062a\u06cc\u060c \u0645\u0642\u062f\u0627\u0631 \u0634\u0627\u0631 \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0644\u0627\u0632\u0645 \u0627\u0633\u062a.",
            )
        if q_platen_init_mw < 0:
            raise DomainError(
                "initial_state_inconsistent",
                "Initial heat input cannot be negative.",
                "\u0634\u0627\u0631 \u062d\u0631\u0627\u0631\u062a\u06cc \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0646\u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u062f \u0645\u0646\u0641\u06cc \u0628\u0627\u0634\u062f.",
                context={"Q_platen_MW": q_platen_init_mw},
            )
        steady = _steady_from_heat(
            float(q_platen_init_mw), t_in, m_total, p_bar, geometry, htc_method
        )
        t_metal = steady["T_metal_C"]
    else:  # previous_run
        if not previous_run:
            raise DomainError("previous_run_not_found")
        try:
            t_metal = float(previous_run["T_metal_C"])
            stored_q = float(previous_run["Q_platen_MW"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DomainError(
                "previous_run_not_found",
                "Stored run does not contain a usable metal temperature and heat input.",
                "\u0634\u0628\u06cc\u0647\u200c\u0633\u0627\u0632\u06cc \u0630\u062e\u06cc\u0631\u0647\u200c\u0634\u062f\u0647 \u062f\u0645\u0627\u06cc \u0641\u0644\u0632 \u0648 \u0634\u0627\u0631 \u0645\u0639\u062a\u0628\u0631 \u0646\u062f\u0627\u0631\u062f.",
            ) from exc
        steady = _steady_from_metal(t_in, t_metal, m_total, p_bar, geometry, htc_method)
        if abs(stored_q - steady["Q_platen_MW"]) > max(2.0, 0.1 * abs(stored_q)):
            warnings.append(
                "Stored heat input was re-balanced against the stored metal temperature "
                f"({stored_q:.1f} MW -> {steady['Q_platen_MW']:.1f} MW) so the node starts in equilibrium."
            )

    t_out = steady["T_out_C"]
    t_mean_steam = steady["T_mean_steam_C"]
    q_gas_mw = steady["Q_platen_MW"]
    diag = steady["diag"]

    if t_metal <= t_mean_steam:
        raise DomainError(
            "initial_state_inconsistent",
            "Metal temperature must exceed the mean steam temperature.",
            "\u062f\u0645\u0627\u06cc \u0641\u0644\u0632 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0634\u200c\u062a\u0631 \u0627\u0632 \u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u062f\u0645\u0627\u06cc \u0628\u062e\u0627\u0631 \u0628\u0627\u0634\u062f.",
            context={"T_metal_C": t_metal, "T_mean_steam_C": t_mean_steam},
        )
    if q_gas_mw < 0:
        raise DomainError(
            "initial_state_inconsistent",
            "Initial heat input cannot be negative.",
            "\u0634\u0627\u0631 \u062d\u0631\u0627\u0631\u062a\u06cc \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0646\u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u062f \u0645\u0646\u0641\u06cc \u0628\u0627\u0634\u062f.",
            context={"Q_platen_MW": q_gas_mw},
        )
    if not (math.isfinite(t_metal) and t_metal <= 900.0):
        raise DomainError(
            "out_of_envelope",
            "Initial metal temperature is not achievable with this heat input.",
            "\u062f\u0645\u0627\u06cc \u0627\u0628\u062a\u062f\u0627\u06cc\u06cc \u0641\u0644\u0632 \u0628\u0627 \u0627\u06cc\u0646 \u0634\u0627\u0631 \u062d\u0631\u0627\u0631\u062a\u06cc \u062f\u0631\u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a.",
            context={"T_metal_C": t_metal, "Q_platen_MW": q_gas_mw},
        )

    conductance = diag["h_W_m2K"] * geometry.inner_area_m2
    residual_w = q_gas_mw * 1e6 - conductance * (t_metal - t_mean_steam)
    capacity = geometry.metal_capacity_j_k
    return {
        "mode": mode,
        "T_metal_C": t_metal,
        "Q_platen_MW": q_gas_mw,
        "stored_Q_platen_MW": stored_q if stored_q is not None else q_gas_mw,
        "T_in_C": t_in,
        "T_out_C": t_out,
        "T_mean_steam_C": t_mean_steam,
        "h_W_m2K": diag["h_W_m2K"],
        "Re": diag["Re"],
        "Nu": diag["Nu"],
        "Pr": diag["Pr"],
        "regime": diag["regime"],
        "NTU": steady["NTU"],
        "m_total_tph": m_total,
        "P_bar": p_bar,
        "h_mix_kJ_kg": mixed["h_mix_kJ_kg"],
        "initial_dTdt_C_per_s": residual_w / capacity,
        "energy_residual_W": residual_w,
        "warnings": warnings,
        "valid": True,
    }


def consistency_residual(initial_state: dict, geometry: PlatenGeometry = DEFAULT_GEOMETRY) -> float:
    """|dT_m/dt| [degC/s] that the initial state would produce at t = 0."""
    return abs(float(initial_state["initial_dTdt_C_per_s"]))


def is_finite_state(state: dict) -> bool:
    """Guard against NaN/inf leaking into a stored run."""
    return all(
        isinstance(state.get(key), (int, float)) and math.isfinite(state[key])
        for key in ("T_metal_C", "Q_platen_MW", "T_in_C", "T_out_C")
    )
