# Pull request — `feature/v4.0.0-platen-superheater-twin` → `main`

**Title**

```
feat: platen superheater digital twin v4.0.0 (FastAPI backend + Compose client)
```

**Base:** `main` (tip `351a25f`)  **Head:** `feature/v4.0.0-platen-superheater-twin` (tip `ab0d9ef`)
**Diff:** 131 files changed, 9 945 insertions(+), 2 252 deletions(−)

---

## Summary

Replaces the v3 on-device Chaquopy calculator with a two-tier architecture: one
authoritative IAPWS-IF97 physics service in Python/FastAPI, and an eight-screen
Kotlin/Compose client that talks to it over REST and WebSocket.

v3 embedded a Python interpreter in the APK, which meant the physics, the API
surface and the UI each carried their own copy of the model, the app could not be
reused as a plant-wide tool, and it stopped at three screens. v4 keeps the model
in exactly one place and makes the client thin.

## What changed

| Area | v3 (`main`) | v4 (this PR) |
| --- | --- | --- |
| Physics | Chaquopy inside the APK | FastAPI service, single source of truth |
| Steam properties | `pyXSteam` wrapper | IAPWS-IF97 (`iapws` 1.5.5), IAPWS 2008/2011 transport |
| Heat transfer | constant | dynamic `h(t)` from `Re`, `Pr`, regime-aware `Nu` |
| Burner model | burner count | 24 tagged burners, per-burner load + ramp, graphical ignition |
| Screens | 3 | 8 (home, steady, transient, burners, results, history, about, settings) |
| Charts | static Compose canvas | interactive ECharts in a WebView |
| History | none | Room on device + SQLite on the server |
| Persian | none | fully Persian RTL About screen, bilingual API errors |
| Tests | 1 script | 76 backend tests + JVM/Compose tests |

## Backend (`backend/`)

- `POST /api/steady`, `POST /api/transient`, `POST /api/burner_startup`,
  `GET /api/properties`, `GET /api/htc`, `POST /api/calibrate`,
  `GET/POST/DELETE /api/runs`, `GET /api/health`, `GET /api/geometry`
- `WSS /ws/transient` (frame replay) and `WSS /ws/burner_startup`
  (live session with `set_burner` commands and gas transport lag)
- Frozen geometry derived once: 43 × 4 = 172 tubes, ≈ 1 108 m² steam-side area,
  13.46 m³, 98.1 t steel, 49.1 MJ/K
- Single-node transient with automatic sub-stepping for stability,
  τ / t63 / t95 reporting; `N > 1` rejected with a typed error
- Pydantic v2 validation, bilingual error objects with stable codes,
  in-memory rate limiting, structured JSON logging
- Dockerfile + docker compose with nginx TLS reverse proxy and WSS upgrade
- Unit-contract test walks the OpenAPI schema and fails on kg/s, Pa-family or
  kelvin fields

## Android client (`app/`)

- Kotlin 2.0.21, AGP 8.5.2, Compose BOM 2024.09.03, Material 3, Hilt 2.52,
  Room 2.6.1 (KSP), Retrofit 2.11 + kotlinx.serialization, OkHttp
- Eight screens, bottom navigation, edge-to-edge, Vazirmatn bundled for Persian
- Interactive charts via ECharts in a WebView with zoom, pan, legend toggles and
  dual value axes
- Results screen exports CSV and PNG and writes runs to Room; history can be
  deleted and reopened
- Settings stores backend URL, default correlation and default operating point

## Unit contract

Unchanged and now enforced end to end: **t/h, °C, bar, MW, W/m²K**. SI is used
only inside the Python solver. Any new field that violates this fails
`backend/tests/test_units_consistency.py`.

## Verification performed

| Check | Result |
| --- | --- |
| `pytest -q` (backend) | 76 passed, exit 0 |
| `./gradlew :app:assembleDebug` | BUILD SUCCESSFUL, 18 MB APK |
| `./gradlew :app:testDebugUnitTest :app:compileDebugAndroidTestKotlin` | exit 0 |
| `aapt dump badging` | `versionCode 4`, `versionName 4.0.0`, `com.steamcalc` |
| Compose UI test on hardware | not run (needs device/emulator) |
| Live backend ↔ app session | not run in this environment |

## Breaking changes and migration

- The v3 app is **not** upgraded in place in terms of behaviour: v4 requires a
  reachable backend for any prediction. History stored by v3 is not migrated
  (v4 uses a new Room schema exported at `app/schemas/…/1.json`).
- `applicationId` stays `com.steamcalc`, so v4 installs over v3 on the same
  device; `versionCode` 4 makes it an upgrade.
- The v3 `app/src/main/python/*` engine and its `tests/test_engine.py` are
  deleted; their physics, corrected and extended, now lives in
  `backend/app/thermo/`.

## Deployment notes

1. Deploy `backend/` (`docker compose up --build -d`) behind TLS; WSS needs the
   nginx upgrade block already provided in `backend/deploy/nginx.conf`.
2. Build the client with `./gradlew :app:assembleDebug` (or a signed release).
3. Set **Settings → Backend URL** to the plant server address on each device;
   the `http://10.0.2.2:8000/` default only applies to an emulator.

## Checklist

- [x] Backend tests green
- [x] Android debug build and JVM tests green
- [x] Documentation updated (`README.md`, `README_fa.md`, `backend/README.md`)
- [x] CI updated: backend tests → Android unit tests → APK artifact
- [ ] Review on a physical device against a live backend
