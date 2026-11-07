"""Endpoint and WebSocket integration tests."""

from __future__ import annotations

STEADY = {
    "m_main_tph": 1000.0,
    "T_main_C": 540.0,
    "P_main_bar": 167.0,
    "m_spray_tph": 30.0,
    "T_LT_out_C": 490.0,
    "Q_platen_MW": 60.0,
    "htc_method": "gnielinski",
}


def test_health_and_geometry(client):
    """Health and geometry endpoints expose the version and frozen geometry."""
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["version"] == "4.0.0"
    geometry = client.get("/api/geometry").json()
    assert geometry["n_tubes"] == 172
    assert 13.0 < geometry["internal_volume_m3"] < 14.0
    assert 97.0 < geometry["metal_mass_kg"] / 1000.0 < 99.0


def test_steady_endpoint(client):
    """Steady prediction returns physically ordered temperatures."""
    response = client.post("/api/steady", json=STEADY)
    assert response.status_code == 200
    body = response.json()
    assert body["T_platen_out_C"] > body["T_platen_in_C"]
    assert body["T_platen_in_C"] < STEADY["T_main_C"]
    assert 3000.0 < body["h_W_m2K"] < 6000.0
    assert body["regime"] == "turbulent"
    assert body["deltaT_spray_C"] == body["T_LT_out_C"] - body["T_platen_in_C"]


def test_steady_endpoint_rejects_out_of_envelope_pressure(client):
    """500 bar is outside the allowed input envelope -> 422 with bilingual text."""
    payload = {**STEADY, "P_main_bar": 500.0}
    response = client.post("/api/steady", json=payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert detail["message_fa"]


def test_steady_endpoint_rejects_if97_invalid_temperature(client):
    """A negative temperature inside the envelope but outside IF97 -> 422."""
    payload = {**STEADY, "T_main_C": -5.0}
    response = client.post("/api/steady", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] in ("out_of_if97_range", "validation_error")


def test_properties_and_htc_endpoints(client):
    """Property and HTC lookups return the IF97 diagnostics."""
    props = client.get("/api/properties", params={"P_bar": 167, "T_C": 540}).json()
    assert props["region"] == 2
    assert 45 < props["rho"] < 55
    htc = client.get(
        "/api/htc", params={"P_bar": 167, "T_C": 500, "m_tph": 1000, "tubes": 172}
    ).json()
    assert htc["regime"] == "turbulent"
    assert 2000 < htc["h_W_m2K"] < 8000
    assert htc["m_dot_tube_tph"] > 0


def test_htc_low_flow_regime_switch(client):
    """Low flow forces Re below 10000 and the laminar regime."""
    htc = client.get(
        "/api/htc", params={"P_bar": 167, "T_C": 500, "m_tph": 1.0, "tubes": 172}
    ).json()
    assert htc["Re"] < 10000
    assert htc["regime"] in ("laminar", "transition")


def test_transient_endpoint_temperature_mode(client):
    """Transient in temperature mode returns aligned series and a tau."""
    payload = {
        **STEADY,
        "duration_s": 120.0,
        "dt_s": 2.0,
        "initial_mode": "temperature",
        "T_metal_init_C": 560.0,
        "htc_method": "gnielinski",
    }
    response = client.post("/api/transient", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["time_s"]) == len(body["T_out_C"]) == len(body["regime"])
    assert body["tau_s"] > 0
    assert body["initial_state"]["T_metal_C"] == 560.0
    assert abs(body["initial_dTdt_C_per_s"]) < 0.01


def test_transient_endpoint_previous_run_mode(client):
    """The seeded baseline run can drive the previous_run mode."""
    runs = client.get("/api/runs").json()
    assert runs
    baseline = runs[-1]
    payload = {
        **STEADY,
        "duration_s": 30.0,
        "dt_s": 2.0,
        "initial_mode": "previous_run",
        "previous_run_id": baseline["id"],
    }
    response = client.post("/api/transient", json=payload)
    assert response.status_code == 200
    assert response.json()["initial_state"]["mode"] == "previous_run"


def test_transient_endpoint_inconsistent_initial_state(client):
    """Metal colder than the steam must answer 422 with the domain code."""
    payload = {
        **STEADY,
        "duration_s": 60.0,
        "dt_s": 2.0,
        "initial_mode": "temperature",
        "T_metal_init_C": 300.0,
    }
    response = client.post("/api/transient", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "initial_state_inconsistent"


def test_burner_layout_and_presets(client):
    """24 burners and the six presets are published."""
    burners = client.get("/api/burners").json()
    assert len(burners) == 24
    presets = client.get("/api/burner_presets").json()
    assert {preset["id"] for preset in presets} >= {"cold_start", "all_on", "all_off"}


def test_burner_startup_endpoint(client):
    """Igniting 4 burners produces fired heat, gas heat and event log."""
    payload = {
        **STEADY,
        "duration_s": 120.0,
        "dt_s": 2.0,
        "initial_mode": "heat_flux",
        "Q_platen_init_MW": 1.0,
        "preset": "four_burners",
        "q_platen_fraction": 0.15,
        "gas_to_metal_lag_s": 5.0,
        "target_T_out_C": 690.0,
    }
    response = client.post("/api/burner_startup", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["Q_burners_MW"]) == len(body["T_out_C"])
    assert body["Q_burners_MW"][-1] > 0
    assert body["Q_gas_MW_platen"][-1] > 0
    assert len(body["burner_events"]) == 4
    assert body["burner_events"][0]["tag"] in {"FA1", "FA2", "FA3", "FA4"}
    assert body["t_reach_T_out_s"] is None


def test_calibration_endpoint(client):
    """Historical points are fitted with a small RMSE on consistent data."""
    payload = {
        "historical": [
            {"T_in_C": 490.0, "T_out_C": 520.0, "m_tph": 1000.0, "P_bar": 167.0},
            {"T_in_C": 480.0, "T_out_C": 512.0, "m_tph": 900.0, "P_bar": 167.0},
            {"T_in_C": 500.0, "T_out_C": 532.0, "m_tph": 1050.0, "P_bar": 167.0},
        ]
    }
    response = client.post("/api/calibrate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert 0 < body["Q_platen_MW_best_fit"] < 400
    assert body["rmse_C"] >= 0
    assert body["n_points"] == 3


def test_run_history_roundtrip(client):
    """Saving, listing, reading and deleting a run works."""
    payload = {
        "kind": "steady",
        "label": "pytest run",
        "T_metal_C": 550.0,
        "Q_platen_MW": 60.0,
        "m_tph": 1000.0,
        "T_in_C": 490.0,
        "T_out_C": 540.0,
        "warnings": [],
        "payload": {"note": "unit test"},
    }
    created = client.post("/api/runs", json=payload)
    assert created.status_code == 201
    run_id = created.json()["id"]
    listed = client.get("/api/runs", params={"limit": 10}).json()
    assert any(run["id"] == run_id for run in listed)
    detail = client.get(f"/api/runs/{run_id}").json()
    assert detail["payload"]["note"] == "unit test"
    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_transient_websocket_streams_frames(client):
    """The transient stream sends ready, frames and a done summary."""
    request = {
        **STEADY,
        "duration_s": 60.0,
        "dt_s": 2.0,
        "initial_mode": "temperature",
        "T_metal_init_C": 560.0,
    }
    with client.websocket_connect("/ws/transient") as websocket:
        websocket.send_json({"type": "start", "speed": 150.0, "request": request})
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        frames = []
        while True:
            message = websocket.receive_json()
            if message["type"] == "done":
                assert "tau_s" in message
                break
            frames.append(message)
        assert len(frames) == 31
        assert all(frame["h_W_m2K"] > 0 for frame in frames)


def test_burner_websocket_accepts_toggles(client):
    """A set_burner command is acknowledged while the live stream runs."""
    request = {
        **STEADY,
        "duration_s": 600.0,
        "dt_s": 0.5,
        "initial_mode": "heat_flux",
        "Q_platen_init_MW": 1.0,
        "preset": "four_burners",
        "q_platen_fraction": 0.15,
        "gas_to_metal_lag_s": 5.0,
    }
    with client.websocket_connect("/ws/burner_startup") as websocket:
        websocket.send_json({"type": "start", "speed": 50.0, "request": request})
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        assert len(ready["burners"]) == 24
        first_frame = websocket.receive_json()
        assert first_frame["type"] == "frame"
        websocket.send_json(
            {
                "action": "set_burner",
                "tag": "FB1",
                "state": "on",
                "target_load_fraction": 1.0,
                "ramp_time_s": 10.0,
            }
        )
        acknowledged = False
        for _ in range(30):
            message = websocket.receive_json()
            if message["type"] == "event_ack":
                assert message["event"]["tag"] == "FB1"
                acknowledged = True
                break
        assert acknowledged
        websocket.send_json({"type": "stop"})
