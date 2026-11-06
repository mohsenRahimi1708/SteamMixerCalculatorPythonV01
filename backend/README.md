# Platen Digital Twin — backend

FastAPI service implementing the IAPWS-IF97 platen superheater model.

## Layout

```
app/
├── main.py                 app factory, lifespan, error handlers, rate limit
├── core/                   config, units, errors (bilingual), logging, rate limit
├── models/schemas.py       Pydantic v2 contract (t/h, °C, bar, MW, W/m²K)
├── api/                    steady, transient, burner, properties, htc,
│                           calibration, runs, WebSocket streams
├── thermo/
│   ├── if97.py             IF97 properties, backward T(P,h), transport correlations
│   ├── htc.py              Re, Pr, regime-aware Nu, h
│   ├── spray.py            adiabatic desuperheater mixing
│   ├── geometry.py         frozen geometry and derived capacitances
│   ├── platen_ss.py        steady solver
│   ├── init_state.py       three initial-condition modes
│   ├── platen_transient.py single-node transient with stable sub-stepping
│   ├── burner.py           24-burner layout, ramps, transport delay, presets
│   └── live_sim.py         stateful session for the burner WebSocket
└── db/                     SQLite connection and run history
```

## Commands

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
PYTHONPATH=. pytest -q
docker compose up --build
```

## Design notes

* All public payloads are validated by Pydantic; anything outside the input
  envelope answers 422 with a bilingual `detail` object.
* Domain errors carry a stable `code` plus English and Persian messages.
* Rate limiting is an in-memory sliding window, exempting `/ws/` and `/docs`.
* Logging is structured JSON with no PII.
* The solver never mutates request state; a transient run is pure apart from the
  SQLite read of a previous run.
* `t63`/`t95` are `null` when a run does not settle; NaN is never serialised.
