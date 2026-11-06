"""Pydantic v2 schemas: the API contract in t/h, degC, bar, MW, W/(m2*K)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

T_FLOW = "mass flow [t/h]"
T_TEMP = "temperature [\u00b0C]"
T_PRESS = "pressure [bar]"
T_POWER = "heat rate [MW]"
T_HTC = "heat transfer coefficient [W/m\u00b2K]"


class HtcMethod(str, Enum):
    """Selectable turbulent heat transfer correlation."""

    dittus_boelter = "dittus_boelter"
    gnielinski = "gnielinski"


class InitialMode(str, Enum):
    """Initial-condition mode of the single-node transient model."""

    temperature = "temperature"
    heat_flux = "heat_flux"
    previous_run = "previous_run"


class BurnerState(str, Enum):
    """Burner command state."""

    on = "on"
    off = "off"


# --------------------------------------------------------------------------- #
# Steady state
# --------------------------------------------------------------------------- #
class SteadyRequest(BaseModel):
    """Steady-state platen prediction request."""

    model_config = ConfigDict(extra="forbid")

    m_main_tph: float = Field(..., gt=0, le=2000, description=f"Main steam {T_FLOW}")
    T_main_C: float = Field(..., ge=-20, le=700, description=f"Main steam {T_TEMP}")
    P_main_bar: float = Field(..., ge=1, le=300, description=f"Main steam {T_PRESS}")
    m_spray_tph: float = Field(0.0, ge=0, le=300, description=f"First-stage spray water {T_FLOW}")
    T_LT_out_C: float = Field(
        490.0, ge=-20, le=700, description=f"Low-temperature superheater outlet {T_TEMP}"
    )
    Q_platen_MW: float = Field(
        60.0, ge=0, le=600, description=f"Heat absorbed by the platen {T_POWER}"
    )
    htc_method: HtcMethod = Field(
        HtcMethod.gnielinski, description="Turbulent correlation: dittus_boelter or gnielinski"
    )


class SteadyResponse(BaseModel):
    """Steady-state result."""

    T_platen_in_C: float = Field(..., description=f"Platen inlet {T_TEMP}")
    T_platen_out_C: float = Field(..., description=f"Platen outlet {T_TEMP}")
    deltaT_spray_C: float = Field(..., description="Spray temperature drop [\u00b0C]")
    heat_absorbed_MW: float = Field(..., description=f"Absorbed heat {T_POWER}")
    Re: float = Field(..., description="Reynolds number")
    Pr: float = Field(..., description="Prandtl number")
    Nu: float = Field(..., description="Nusselt number")
    Nu_DB: float = Field(..., description="Dittus-Boelter Nusselt number")
    Nu_Gnielinski: float = Field(..., description="Gnielinski Nusselt number")
    f: float = Field(..., description="Darcy friction factor")
    h_W_m2K: float = Field(..., description=T_HTC)
    regime: str = Field(..., description="laminar, transition or turbulent")
    mu_Pas: float = Field(..., description="Dynamic viscosity [Pa\u00b7s]")
    k_W_mK: float = Field(..., description="Thermal conductivity [W/(m\u00b7K)]")
    cp_kJ_kgK: float = Field(..., description="Specific heat [kJ/(kg\u00b7K)]")
    h_main_kJ_kg: float = Field(..., description="Main steam specific enthalpy [kJ/kg]")
    h_spray_kJ_kg: float = Field(..., description="Saturated-liquid spray enthalpy [kJ/kg]")
    h_mix_kJ_kg: float = Field(..., description="Mixed specific enthalpy [kJ/kg]")
    m_total_tph: float = Field(..., description=f"Total steam {T_FLOW}")
    m_main_tph: float = Field(..., description=f"Main steam {T_FLOW}")
    m_spray_tph: float = Field(..., description=f"Spray {T_FLOW}")
    T_main_C: float = Field(..., description=f"Main steam {T_TEMP}")
    T_LT_out_C: float = Field(..., description=f"Low-temperature superheater outlet {T_TEMP}")
    P_bar: float = Field(..., description=T_PRESS)
    Q_platen_MW: float = Field(..., description=T_POWER)
    htc_method: str
    NTU: float = Field(..., description="Number of transfer units of the platen")
    warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Transient
# --------------------------------------------------------------------------- #
class TransientRequest(SteadyRequest):
    """Transient request: steady fields plus time-stepping and initial state."""

    duration_s: float = Field(600.0, gt=0, le=7200, description="Simulated duration [s]")
    dt_s: float = Field(2.0, gt=0, le=60, description="Output time step [s]")
    initial_mode: InitialMode = Field(
        InitialMode.temperature,
        description="temperature, heat_flux or previous_run",
    )
    T_metal_init_C: float | None = Field(
        None, ge=0, le=900, description="Initial metal temperature [\u00b0C]"
    )
    Q_platen_init_MW: float | None = Field(
        None, ge=0, le=900, description=f"Initial gas-side heat input {T_POWER}"
    )
    previous_run_id: str | None = Field(
        None, description="Stored run identifier used by the previous_run mode"
    )
    heating: bool = Field(True, description="Steam is heated (n = 0.4) rather than cooled")
    n_nodes: int = Field(1, ge=1, le=50, description="Number of metal nodes (1 in this version)")

    @model_validator(mode="after")
    def _check_mode(self) -> "TransientRequest":
        if self.initial_mode == InitialMode.temperature and self.T_metal_init_C is None:
            raise ValueError("T_metal_init_C is required when initial_mode = temperature")
        if self.initial_mode == InitialMode.heat_flux and self.Q_platen_init_MW is None:
            raise ValueError("Q_platen_init_MW is required when initial_mode = heat_flux")
        if self.initial_mode == InitialMode.previous_run and not self.previous_run_id:
            raise ValueError("previous_run_id is required when initial_mode = previous_run")
        return self


class InitialStateOut(BaseModel):
    """Resolved initial state of the metal node."""

    mode: str
    T_metal_C: float = Field(..., description=f"Metal {T_TEMP}")
    Q_platen_MW: float = Field(..., description=f"Gas-side heat input {T_POWER}")
    T_in_C: float = Field(..., description=f"Platen inlet steam {T_TEMP}")
    T_out_C: float = Field(..., description=f"Platen outlet steam {T_TEMP}")
    T_mean_steam_C: float = Field(..., description=f"Mean steam {T_TEMP}")
    h_W_m2K: float = Field(..., description=T_HTC)
    Re: float
    Nu: float
    Pr: float
    regime: str
    NTU: float
    m_total_tph: float = Field(..., description=f"Total steam {T_FLOW}")
    P_bar: float = Field(..., description=T_PRESS)
    h_mix_kJ_kg: float
    initial_dTdt_C_per_s: float
    energy_residual_W: float
    valid: bool


class TransientResponse(BaseModel):
    """Transient result series, all in API units."""

    time_s: list[float] = Field(..., description="Time [s]")
    T_in_C: list[float] = Field(..., description=f"Platen inlet {T_TEMP}")
    T_out_C: list[float] = Field(..., description=f"Platen outlet {T_TEMP}")
    T_metal_C: list[float] = Field(..., description=f"Metal {T_TEMP}")
    Q_MW: list[float] = Field(..., description=f"Gas-side heat input {T_POWER}")
    Q_gas_MW: list[float] = Field(..., description=f"Gas-side heat input {T_POWER}")
    Q_steam_MW: list[float] = Field(..., description=f"Heat into the steam {T_POWER}")
    Q_conv_MW: list[float] = Field(..., description="Convective heat to the steam [MW] (negative = metal cooled)")
    Re: list[float]
    Pr: list[float]
    Nu: list[float]
    h_W_m2K: list[float] = Field(..., description=T_HTC)
    regime: list[str]
    tau_s: float = Field(..., description="Effective thermal time constant [s]")
    t63_s: float | None = Field(None, description="63 % settling time [s], null when not reached")
    t95_s: float | None = Field(None, description="95 % settling time [s], null when not reached")
    duration_s: float
    dt_s: float
    n_steps: int
    substeps_max: int
    warnings: list[str] = Field(default_factory=list)
    initial_state: InitialStateOut
    initial_dTdt_C_per_s: float
    T_in_C_value: float = Field(..., description=f"Constant platen inlet {T_TEMP}")
    m_total_tph: float = Field(..., description=f"Total steam {T_FLOW}")
    P_bar: float = Field(..., description=T_PRESS)
    htc_method: str
    n_nodes: int
    geometry: dict[str, Any]


# --------------------------------------------------------------------------- #
# Burners
# --------------------------------------------------------------------------- #
class BurnerEventInput(BaseModel):
    """One burner ignition or shutdown command."""

    model_config = ConfigDict(extra="forbid")

    tag: str = Field(..., description="Burner tag, e.g. FA1 ... RC4")
    time_s: float = Field(
        0.0, ge=0, le=7200, description="Command time in simulated seconds [s]"
    )
    ignition_time_s: float | None = Field(
        None, ge=0, le=7200, description="Alias of time_s [s]"
    )
    state: BurnerState = Field(BurnerState.on)
    target_load_fraction: float = Field(1.0, ge=0, le=1, description="Target load fraction 0..1")
    ramp_time_s: float = Field(30.0, ge=0, le=1800, description="Linear load ramp [s]")

    def effective_time(self) -> float:
        return self.ignition_time_s if self.ignition_time_s is not None else self.time_s


class BurnerStartupRequest(TransientRequest):
    """Burner start/stop simulation request (steady + transient + schedule)."""

    burner_schedule: list[BurnerEventInput] = Field(default_factory=list)
    preset: str | None = Field(
        None, description="Named preset used when burner_schedule is empty"
    )
    q_platen_fraction: float = Field(
        0.15, ge=0, le=1, description="Fraction of fired heat absorbed by the platen"
    )
    gas_to_metal_lag_s: float = Field(
        5.0, ge=0, le=120, description="Furnace gas transport delay [s]"
    )
    target_T_out_C: float | None = Field(None, ge=0, le=700, description=f"Target outlet {T_TEMP}")
    target_T_metal_C: float | None = Field(None, ge=0, le=900, description=f"Target metal {T_TEMP}")


class BurnerEventOut(BaseModel):
    """Logged burner event."""

    tag: str
    level: str
    row: str
    time_s: float
    state: str
    target_load_fraction: float
    ramp_time_s: float


class BurnerStartupResponse(TransientResponse):
    """Transient response plus fired heat, gas heat and the burner event log."""

    Q_burners_MW: list[float] = Field(..., description=f"Fired heat {T_POWER}")
    Q_gas_MW_platen: list[float] = Field(..., description=f"Gas heat to the platen {T_POWER}")
    burner_events: list[BurnerEventOut] = Field(default_factory=list)
    burner_states_final: dict[str, float] = Field(default_factory=dict)
    t_reach_T_out_s: float | None = Field(None, description="Time to reach target outlet [s]")
    t_reach_T_metal_s: float | None = Field(None, description="Time to reach target metal [s]")
    q_platen_fraction: float
    gas_to_metal_lag_s: float


# --------------------------------------------------------------------------- #
# Properties / HTC / calibration / runs
# --------------------------------------------------------------------------- #
class PropertiesResponse(BaseModel):
    """IF97 property set."""

    P_bar: float = Field(..., description=T_PRESS)
    T_C: float = Field(..., description=T_TEMP)
    region: int | None = Field(..., description="IF97 region number")
    rho: float = Field(..., description="Density [kg/m\u00b3]")
    v: float = Field(..., description="Specific volume [m\u00b3/kg]")
    h: float = Field(..., description="Specific enthalpy [kJ/kg]")
    s: float = Field(..., description="Specific entropy [kJ/(kg\u00b7K)]")
    cp: float = Field(..., description="Specific heat [kJ/(kg\u00b7K)]")
    mu: float = Field(..., description="Dynamic viscosity [Pa\u00b7s]")
    k: float = Field(..., description="Thermal conductivity [W/(m\u00b7K)]")
    w: float = Field(..., description="Speed of sound [m/s]")


class HtcResponse(BaseModel):
    """Heat transfer coefficient diagnostics."""

    Re: float
    Pr: float
    Nu: float
    Nu_DB: float
    Nu_Gnielinski: float
    f: float
    h_W_m2K: float = Field(..., description=T_HTC)
    regime: str
    mu_Pas: float = Field(..., description="Dynamic viscosity [Pa\u00b7s]")
    k_W_mK: float = Field(..., description="Thermal conductivity [W/(m\u00b7K)]")
    cp_kJ_kgK: float = Field(..., description="Specific heat [kJ/(kg\u00b7K)]")
    m_dot_tube_tph: float = Field(..., description=f"Per-tube {T_FLOW}")
    m_total_tph: float = Field(..., description=f"Total {T_FLOW}")
    n_tubes: int
    d_i_m: float
    P_bar: float = Field(..., description=T_PRESS)
    T_C: float = Field(..., description=T_TEMP)
    method: str
    heating: bool


class CalibrationPoint(BaseModel):
    """One historical operating point."""

    model_config = ConfigDict(extra="forbid")

    T_in_C: float = Field(..., ge=-20, le=700, description=f"Platen inlet {T_TEMP}")
    T_out_C: float = Field(..., ge=-20, le=700, description=f"Platen outlet {T_TEMP}")
    m_tph: float = Field(..., gt=0, le=2000, description=f"Steam {T_FLOW}")
    P_bar: float = Field(..., ge=1, le=300, description=T_PRESS)


class CalibrationRequest(BaseModel):
    """Historical data used to fit Q_platen."""

    model_config = ConfigDict(extra="forbid")

    historical: list[CalibrationPoint] = Field(..., min_length=1, max_length=500)


class CalibrationResponse(BaseModel):
    """Best-fit platen heat absorption."""

    Q_platen_MW_best_fit: float = Field(..., description=f"Absorbed heat {T_POWER}")
    rmse_C: float = Field(..., description="Root-mean-square outlet error [\u00b0C]")
    n_points: int
    residuals_C: list[float] = Field(..., description="Per-point outlet residuals [\u00b0C]")
    Q_per_point_MW: list[float] = Field(..., description=f"Absorbed heat per point {T_POWER}")


class RunSummary(BaseModel):
    """Stored run (history)."""

    id: str
    created_at: str
    kind: str
    label: str
    T_metal_C: float
    Q_platen_MW: float
    m_tph: float
    T_in_C: float
    T_out_C: float
    warnings: list[str] = Field(default_factory=list)


class RunDetail(RunSummary):
    """Stored run with its full payload."""

    payload: dict[str, Any]


class RunCreate(BaseModel):
    """Client-side save of a completed run."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., description="steady, transient, burner_startup or baseline")
    label: str = Field(..., max_length=160)
    T_metal_C: float = Field(..., description=f"Metal {T_TEMP}")
    Q_platen_MW: float = Field(..., description=f"Gas-side heat input {T_POWER}")
    m_tph: float = Field(..., description=f"Steam {T_FLOW}")
    T_in_C: float = Field(..., description=f"Platen inlet {T_TEMP}")
    T_out_C: float = Field(..., description=f"Platen outlet {T_TEMP}")
    warnings: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class BurnerSpecOut(BaseModel):
    """Static burner description."""

    tag: str
    level: str
    row: str
    index: int
    elevation_m: float
    lateral_m: float
    rated_MW: float


class BurnerPresetOut(BaseModel):
    """Burner preset description."""

    id: str
    event_count: int
    label_en: str
    label_fa: str


class WsToggleCommand(BaseModel):
    """Client -> server burner toggle command."""

    action: Literal["set_burner"] = "set_burner"
    tag: str
    state: BurnerState
    target_load_fraction: float = Field(1.0, ge=0, le=1)
    ramp_time_s: float = Field(30.0, ge=0, le=1800)


class WsTransientStart(BaseModel):
    """Client -> server start command for the transient stream."""

    type: Literal["start"] = "start"
    speed: float = Field(10.0, gt=0, le=200, description="simulated seconds per wall second")
    request: TransientRequest


class WsBurnerStart(BaseModel):
    """Client -> server start command for the burner stream."""

    type: Literal["start"] = "start"
    speed: float = Field(1.0, gt=0, le=200, description="simulated seconds per wall second")
    request: BurnerStartupRequest


class HealthResponse(BaseModel):
    """Service health."""

    status: str
    version: str
    if97: str
