"""Unit consistency across the published OpenAPI contract.

The API may only speak t/h, degC, bar, MW and W/(m2K).  This test fails if a
flow in kg/s, a pressure in MPa/kPa/Pa or a temperature in K leaks into any
schema field name, description or query parameter.
"""

from __future__ import annotations

import re

import pytest

FORBIDDEN_DESCRIPTION_PATTERNS = [
    (re.compile(r"kg\s*/\s*s"), "mass flow in kg/s"),
    (re.compile(r"\bkg\s+s\b"), "mass flow in kg/s"),
    (re.compile(r"\b[GMk]?Pa\b(?!\s*·\s*s)"), "pressure in Pa-family units"),
    (re.compile(r"\u00b0\s*K\b"), "temperature in kelvin"),
    (re.compile(r"\bkelvin\b", re.IGNORECASE), "temperature in kelvin"),
]

FORBIDDEN_NAME_PATTERNS = [
    (re.compile(r"_(kgs|kg_s|kgps)$"), "field name with kg/s"),
    (re.compile(r"_(MPa|kPa|Pa)$"), "field name with Pa-family units"),
    (re.compile(r"_K$"), "field name with kelvin"),
]


def _walk_schemas(schema: dict):
    """Yield (name, description) for every property in the components."""
    for schema_name, definition in schema.get("components", {}).get("schemas", {}).items():
        for prop_name, prop in definition.get("properties", {}).items():
            yield f"{schema_name}.{prop_name}", prop_name, prop.get("description", "")


def _walk_parameters(schema: dict):
    """Yield (name, description) for every query parameter."""
    for path, operations in schema.get("paths", {}).items():
        for method, operation in operations.items():
            for parameter in operation.get("parameters", []):
                yield f"{method.upper()} {path} {parameter.get('name')}", parameter.get(
                    "name", ""
                ), parameter.get("description", "")


def test_no_forbidden_units_in_openapi(client):
    """No kg/s, Pa-family pressures or kelvin temperatures anywhere."""
    schema = client.get("/openapi.json").json()
    offenders: list[str] = []
    for label, name, description in list(_walk_schemas(schema)) + list(_walk_parameters(schema)):
        for pattern, reason in FORBIDDEN_DESCRIPTION_PATTERNS:
            if pattern.search(description):
                offenders.append(f"{label}: {reason} -> {description!r}")
        for pattern, reason in FORBIDDEN_NAME_PATTERNS:
            if pattern.search(name):
                offenders.append(f"{label}: {reason}")
    assert not offenders, "Forbidden units in the API contract:\n" + "\n".join(offenders)


def test_required_units_are_present():
    """The main flow / temperature / pressure fields document their units."""
    schema = client_get_schema()
    steady = schema["components"]["schemas"]["SteadyRequest"]["properties"]
    assert "t/h" in steady["m_main_tph"]["description"]
    assert "\u00b0C" in steady["T_main_C"]["description"]
    assert "bar" in steady["P_main_bar"]["description"]
    assert "MW" in steady["Q_platen_MW"]["description"]
    transient = schema["components"]["schemas"]["TransientResponse"]["properties"]
    assert "W/m\u00b2K" in transient["h_W_m2K"]["description"]


def client_get_schema() -> dict:
    """Local helper importing the app lazily to keep module import cheap."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as client:
        return client.get("/openapi.json").json()


@pytest.mark.parametrize(
    "path",
    ["/api/steady", "/api/transient", "/api/burner_startup", "/api/htc", "/api/properties"],
)
def test_documented_endpoints_exist(path):
    """Every documented endpoint is published."""
    schema = client_get_schema()
    assert path in schema["paths"]
