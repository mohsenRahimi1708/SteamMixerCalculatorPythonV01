"""Q_platen calibration from historical operating data."""

from __future__ import annotations

import math

from fastapi import APIRouter

from app.core.errors import DomainError
from app.models.schemas import CalibrationRequest, CalibrationResponse
from app.thermo import if97

router = APIRouter(tags=["calibration"])


@router.post("/api/calibrate", response_model=CalibrationResponse, summary="Fit platen heat absorption")
def calibrate(request: CalibrationRequest) -> dict:
    """Least-squares fit of a constant platen heat absorption to historical data.

    Each point contributes Q = m_dot * (h_out - h_in); the fit minimises the
    outlet temperature RMSE over the whole set.
    """
    if not request.historical:
        raise DomainError("no_calibration_data")
    q_per_point: list[float] = []
    points = request.historical
    for point in points:
        h_in = if97.h_pt(point.P_bar, point.T_in_C)
        h_out = if97.h_pt(point.P_bar, point.T_out_C)
        q_per_point.append(point.m_tph * (h_out - h_in) / 3600.0)
    q_fit = sum(q_per_point) / len(q_per_point)

    residuals: list[float] = []
    for point in points:
        h_in = if97.h_pt(point.P_bar, point.T_in_C)
        h_pred = h_in + q_fit * 3600.0 / point.m_tph
        t_pred = if97.t_ph(point.P_bar, h_pred)
        residuals.append(t_pred - point.T_out_C)
    rmse = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    return {
        "Q_platen_MW_best_fit": q_fit,
        "rmse_C": rmse,
        "n_points": len(points),
        "residuals_C": residuals,
        "Q_per_point_MW": q_per_point,
    }
