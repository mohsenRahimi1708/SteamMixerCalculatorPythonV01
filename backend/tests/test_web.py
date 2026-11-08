"""The browser HMI is served by the same app as the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_the_hmi() -> None:
    """GET / returns the single-page HMI, not a 404."""
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "Platen Superheater" in body
    assert "transient-chart" in body
    assert "burner-grid" in body
    assert 'dir="rtl"' in body  # Persian About section


def test_hmi_assets_are_served() -> None:
    """JavaScript, CSS, ECharts and the Vazirmatn font all resolve."""
    with TestClient(app) as client:
        for path, content_type in (
            ("/app.js", "javascript"),
            ("/style.css", "text/css"),
            ("/vendor/echarts.min.js", "javascript"),
            ("/vendor/vazirmatn.ttf", "font"),
        ):
            response = client.get(path)
            assert response.status_code == 200, path
            assert content_type in response.headers["content-type"], path


def test_api_and_docs_still_work_with_the_mount() -> None:
    """The catch-all mount must not shadow /api or /docs."""
    with TestClient(app) as client:
        health = client.get("/api/health")
        docs = client.get("/docs")
        steady = client.post(
            "/api/steady",
            json={
                "m_main_tph": 1000,
                "T_main_C": 540,
                "P_main_bar": 167,
                "m_spray_tph": 30,
                "T_LT_out_C": 490,
                "Q_platen_MW": 60,
                "htc_method": "gnielinski",
            },
        )
    assert health.status_code == 200
    assert docs.status_code == 200
    assert steady.status_code == 200
    assert steady.json()["T_platen_out_C"] > 500


def test_hmi_never_leaks_foreign_units() -> None:
    """The UI text only mentions the five contractual units."""
    with TestClient(app) as client:
        body = client.get("/").text + client.get("/app.js").text
    for forbidden in ("kg/s", " kPa", ">K<"):
        assert forbidden not in body
    for unit in ("t/h", "°C", "bar", "MW", "W/m²K"):
        assert unit in body
