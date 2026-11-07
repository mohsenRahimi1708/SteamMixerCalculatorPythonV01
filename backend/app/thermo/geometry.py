"""Platen superheater geometry and lumped thermal capacitance.

Frozen geometry of the 325 MW unit platen superheater (1990s two-pass,
natural-circulation boiler):

    43 panels x 4 parallel serpentine tubes = 172 tubes
    8 passes x 6 m = 48 m straight, 50 m developed length per tube
    tube 57 mm OD x 8 mm wall (12Cr1MoV)
    headers 400 mm OD x 55 mm wall, 16 m long, inlet 34.774 m / outlet 31.880 m

Every secondary quantity (inner area, internal volume, metal mass, heat
capacities, thermal time constant) is derived here, never hard-coded twice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.units import tph_to_kgs, FLOW_UNIT, TEMP_UNIT
from app.thermo import if97


@dataclass(frozen=True)
class PlatenGeometry:
    """Frozen geometry of one platen superheater."""

    n_panels: int = 43
    tubes_per_panel: int = 4
    n_passes: int = 8
    pass_length_m: float = 6.0
    developed_length_m: float = 50.0
    tube_od_m: float = 0.057
    tube_wall_m: float = 0.008
    tube_material: str = "12Cr1MoV"
    #: Specific heat of 12Cr1MoV at 450-500 degC [J/(kg*K)].
    metal_cp_j_kgk: float = 500.0
    metal_density_kg_m3: float = 7850.0
    header_od_m: float = 0.400
    header_wall_m: float = 0.055
    header_length_m: float = 16.0
    n_headers: int = 2
    header_inlet_elevation_m: float = 34.774
    header_outlet_elevation_m: float = 31.880
    header_width_m: float = 16.0
    inlet_steam_paths_per_header: int = 2
    #: Distance of each flow path from the header end [m] (8 m apart).
    steam_path_offset_m: float = 4.0
    #: Design point used for the nominal time constant.
    design_flow_tph: float = 1000.0
    design_pressure_bar: float = 167.0
    design_T_main_C: float = 540.0
    design_T_platen_in_C: float = 490.0
    design_T_platen_out_C: float = 540.0
    #: Metal heat capacity published for this unit [J/K] (cross-check only).
    reference_metal_capacity_j_k: float = 49.1e6
    reference_steam_capacity_j_k: float = 1.39e6
    reference_tau_s: float = 79.0

    # --- derived tube quantities -----------------------------------------
    @property
    def n_tubes(self) -> int:
        """Total number of parallel tubes (43 panels x 4 tubes)."""
        return self.n_panels * self.tubes_per_panel

    @property
    def tube_id_m(self) -> float:
        """Tube inner diameter [m]."""
        return self.tube_od_m - 2.0 * self.tube_wall_m

    @property
    def d_i_m(self) -> float:
        """Alias of :attr:`tube_id_m` used by the heat transfer module."""
        return self.tube_id_m

    @property
    def inner_area_m2(self) -> float:
        """Total steam-side wetted area [m2]."""
        return self.n_tubes * self.developed_length_m * math.pi * self.tube_id_m

    @property
    def tube_internal_volume_m3(self) -> float:
        """Internal volume of all tubes [m3]."""
        return self.n_tubes * self.developed_length_m * math.pi / 4.0 * self.tube_id_m ** 2

    @property
    def header_id_m(self) -> float:
        """Header inner diameter [m]."""
        return self.header_od_m - 2.0 * self.header_wall_m

    @property
    def header_internal_volume_m3(self) -> float:
        """Internal volume of all headers [m3]."""
        return (
            self.n_headers
            * self.header_length_m
            * math.pi
            / 4.0
            * self.header_id_m ** 2
        )

    @property
    def internal_volume_m3(self) -> float:
        """Total internal steam volume [m3] (tubes + headers)."""
        return self.tube_internal_volume_m3 + self.header_internal_volume_m3

    @property
    def tube_metal_mass_kg(self) -> float:
        """Mass of all tubes [kg]."""
        area = math.pi / 4.0 * (self.tube_od_m ** 2 - self.tube_id_m ** 2)
        return area * self.developed_length_m * self.n_tubes * self.metal_density_kg_m3

    @property
    def header_metal_mass_kg(self) -> float:
        """Mass of all headers [kg]."""
        area = math.pi / 4.0 * (self.header_od_m ** 2 - self.header_id_m ** 2)
        return area * self.header_length_m * self.n_headers * self.metal_density_kg_m3

    @property
    def metal_mass_kg(self) -> float:
        """Total metal mass of tubes plus headers [kg]."""
        return self.tube_metal_mass_kg + self.header_metal_mass_kg

    @property
    def metal_capacity_j_k(self) -> float:
        """Metal heat capacity M*C [J/K]."""
        return self.metal_mass_kg * self.metal_cp_j_kgk

    @property
    def panel_pitch_m(self) -> float:
        """Panel pitch along the header [m] (16 / 43)."""
        return self.header_width_m / self.n_panels

    def steam_mass_kg(self, p_bar: float | None = None, t_c: float | None = None) -> float:
        """Steam inventory inside the platen [kg] at the given (or design) state."""
        p = p_bar if p_bar is not None else self.design_pressure_bar
        t = t_c if t_c is not None else 0.5 * (self.design_T_platen_in_C + self.design_T_platen_out_C)
        props = if97.props_pt(p, t)
        return self.internal_volume_m3 * float(props["rho"])

    def steam_capacity_j_k(self, p_bar: float | None = None, t_c: float | None = None) -> float:
        """Steam heat capacity M_steam*cp [J/K] at the given (or design) state."""
        p = p_bar if p_bar is not None else self.design_pressure_bar
        t = t_c if t_c is not None else 0.5 * (self.design_T_platen_in_C + self.design_T_platen_out_C)
        props = if97.props_pt(p, t)
        return self.steam_mass_kg(p, t) * float(props["cp"]) * 1000.0

    def total_capacity_j_k(self, p_bar: float | None = None, t_c: float | None = None) -> float:
        """Metal plus steam heat capacity [J/K]."""
        return self.metal_capacity_j_k + self.steam_capacity_j_k(p_bar, t_c)

    def tau_s(
        self,
        m_total_tph: float,
        p_bar: float | None = None,
        t_c: float | None = None,
    ) -> float:
        """Effective thermal time constant [s], (M_m*C_m + M_s*C_s)/(m_dot*cp)."""
        if m_total_tph <= 0:
            return math.inf
        p = p_bar if p_bar is not None else self.design_pressure_bar
        t = t_c if t_c is not None else 0.5 * (self.design_T_platen_in_C + self.design_T_platen_out_C)
        cp = float(if97.props_pt(p, t)["cp"]) * 1000.0
        return self.total_capacity_j_k(p, t) / (tph_to_kgs(m_total_tph) * cp)

    def as_dict(self) -> dict:
        """Geometry summary in API units (t/h, degC, bar, MW, W/m2K)."""
        return {
            "n_panels": self.n_panels,
            "tubes_per_panel": self.tubes_per_panel,
            "n_tubes": self.n_tubes,
            "n_passes": self.n_passes,
            "pass_length_m": self.pass_length_m,
            "developed_length_m": self.developed_length_m,
            "tube_od_m": self.tube_od_m,
            "tube_wall_m": self.tube_wall_m,
            "tube_id_m": self.tube_id_m,
            "tube_material": self.tube_material,
            "inner_area_m2": self.inner_area_m2,
            "internal_volume_m3": self.internal_volume_m3,
            "metal_mass_kg": self.metal_mass_kg,
            "metal_capacity_MJ_K": self.metal_capacity_j_k / 1e6,
            "steam_capacity_MJ_K": self.steam_capacity_j_k() / 1e6,
            "total_capacity_MJ_K": self.total_capacity_j_k() / 1e6,
            "tau_s": self.tau_s(self.design_flow_tph),
            "header_inlet_elevation_m": self.header_inlet_elevation_m,
            "header_outlet_elevation_m": self.header_outlet_elevation_m,
            "panel_pitch_m": self.panel_pitch_m,
            "design_flow_unit": FLOW_UNIT,
            "design_temperature_unit": TEMP_UNIT,
        }


DEFAULT_GEOMETRY = PlatenGeometry()
