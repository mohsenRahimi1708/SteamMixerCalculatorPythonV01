# Platen Superheater Digital Twin — v4.0.0

Steady-state, transient and graphical burner start/stop model of the platen
superheater of a 325 MW natural-circulation steam power plant boiler.

* **Android client** — Kotlin, Jetpack Compose, Material 3, Hilt, Room, RTL-aware.
* **Backend** — Python 3.11, FastAPI, Uvicorn, IAPWS-IF97 (via `iapws`), SQLite.
* **Charts** — WebView + Apache ECharts (zoom, pan, legend toggling, tooltips).
* **Transport** — HTTPS REST + WSS streaming (t/h, °C, bar, MW, W/m²K).

This release replaces the v3 on-device Chaquopy engine with a real plant-server
architecture: one authoritative physics implementation, shared by the REST API,
the WebSocket streams and every client.

---

## 1. Version and branch

| Item | Value |
| --- | --- |
| Version | `4.0.0` (Android `versionCode` 4, backend `4.0.0`) |
| Branch | `feature/v4.0.0-platen-superheater-twin` |
| Previous release | `3.0.0` — Steam Mixer Calculator (JVM Chaquopy engine, 3 screens) |

What changed from v3:

| Area | v3 | v4 |
| --- | --- | --- |
| Physics location | Chaquopy Python inside the APK | FastAPI service (single source of truth) |
| Property library | `pyXSteam` wrapper | IAPWS-IF97 + IAPWS 2008/2011 transport correlations |
| Screens | 3 (spray, impact, transient) | 8 (dashboard, steady, transient, burners, results, history, about, settings) |
| Heat transfer | constant / not modelled | dynamic `h(t)` from `Re`, `Pr`, regime-aware `Nu` (Dittus–Boelter and Gnielinski) |
| Burner model | number of burners only | 24 tagged burners, per-burner load and ramp, graphical ignition |
| Charts | static Compose canvas | interactive ECharts in a WebView |
| History | none | Room (device) + SQLite (server) |
| Persian | none | full RTL About screen, bilingual error messages |

---

## 2. Unit contract (enforced)

Everything the user can see or send uses exactly these units:

| Quantity | Unit |
| --- | --- |
| Mass flow | **t/h** |
| Temperature | **°C** |
| Pressure | **bar** |
| Heat rate | **MW** |
| Heat transfer coefficient | **W/m²K** |

SI is used only inside the solver (kg/s, K, Pa) at the function boundary. A test
(`backend/tests/test_units_consistency.py`) walks the published OpenAPI schema and
fails if a flow in kg/s, a pressure in Pa-family units or a temperature in kelvin
leaks into any field name or description.

---

## 3. Physics

### 3.1 Frozen geometry (`backend/app/thermo/geometry.py`)

| Property | Value |
| --- | --- |
| Panels × tubes | 43 × 4 = 172 tubes |
| Tube | 57 mm OD × 8 mm wall, 12Cr1MoV, 50 m developed length |
| Headers | 2 × 400 mm OD × 55 mm wall × 16 m |
| Steam-side area | ≈ 1108 m² |
| Internal volume | ≈ 13.46 m³ |
| Metal mass | ≈ 98.1 t |
| Metal heat capacity | ≈ 49.1 MJ/K |
| Time constant at 1000 t/h | ≈ 60–70 s (published 79 s uses cp = 2.3 kJ/(kg·K); IF97 gives ≈ 2.9 at 515 °C) |

Every derived quantity (area, volume, mass, capacitance) is computed from the
geometry, never hard-coded twice.

### 3.2 Steady state

```
h_main  = h(P, T_main)                      # region 2
h_spray = h_f(P)                            # saturated liquid, region 1
h_mix   = (m_main·h_main + m_spray·h_spray) / (m_main + m_spray)
T_in    = T(P, h_mix)
Δh      = Q_platen · 3600 / m_total          # kJ/kg
T_out   = T(P, h_mix + Δh)
h, Re, Nu, regime = HTC(P, (T_in + T_out)/2, m_total)
```

### 3.3 Transient (single node, N = 1)

```
T_out = T_in + h·A·(T_m − T̄_s) / (m_dot·cp)          # T̄_s = (T_in + T_out)/2
Q_conv = h·A·(T̄_s − T_m)
dT_m/dt = (Q_gas + Q_conv) / (M_m·C_m)
```

The implicit `T_out` relation is solved in closed form, and the explicit metal
update is internally sub-stepped to satisfy `dt ≤ 0.5·M·C/(h·A)`. The solver
exposes τ_eff, t63 and t95 and refuses `N ≠ 1` with a dedicated error until
Phase 2 lands.

### 3.4 Dynamic heat transfer coefficient

```
Re = 4·m_dot_tube / (π·d_i·μ)      Pr = μ·cp/k
Re < 2300        → laminar,    Nu = 4.36
2300 ≤ Re < 10⁴  → transition, log-linear interpolation
Re ≥ 10⁴         → turbulent,  Dittus–Boelter or Gnielinski (selectable)
h = Nu·k/d_i
```

`Re`, `Pr`, `Nu`, both `Nu` correlations, `f`, `h`, `μ`, `k`, `cp` and the regime
are all returned by `/api/htc` and inside every transient frame.

### 3.5 Burner start / stop

24 burners (40 MW each, 960 MW total) on three levels at 9/12/15 m, front and
rear rows, four per row:

```
Q_burners(t) = Σ_i 40 MW · load_i(t)          # linear ramp per burner
Q_gas(t)     = q_platen_fraction · Q_burners(t − gas_lag)   # defaults 0.15, 5 s
```

The live WebSocket session applies client ignition/shutdown commands at the
current simulation time, so `T_out(t)` and `T_metal(t)` answer within a few time
constants. Warning flags: `T_metal > 600 °C`, `|dT/dt| > 5 °C/min`, `Re` entering
the transition/laminar band.

---

## 4. Backend

### 4.1 Run

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Swagger UI: <http://localhost:8000/docs>

Docker (backend + nginx reverse proxy with WSS upgrade):

```bash
cd backend
docker compose up --build -d      # http://localhost:8080
```

For production TLS, mount `platensh.crt` / `platensh.key` into
`backend/deploy/certs` and use the 8443 listener.

### 4.2 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/steady` | steady-state platen prediction |
| POST | `/api/transient` | single-node transient series |
| POST | `/api/burner_startup` | burner schedule simulation |
| GET | `/api/properties` | IF97 state point |
| GET | `/api/htc` | heat transfer diagnostics |
| POST | `/api/calibrate` | least-squares `Q_platen` fit |
| GET | `/api/burners` / `/api/burner_presets` | layout and presets |
| GET/POST/DELETE | `/api/runs` | server-side history |
| GET | `/api/health` / `/api/geometry` | service and geometry |
| WSS | `/ws/transient` | frame-by-frame replay of a transient |
| WSS | `/ws/burner_startup` | live burner session + `set_burner` commands |

WebSocket start frame:

```json
{"type":"start","speed":1.0,"request":{ "...BurnerStartupRequest..." }}
```

Live commands:

```json
{"action":"set_burner","tag":"FA1","state":"on","target_load_fraction":1.0,"ramp_time_s":30}
```

Errors are bilingual:

```json
{"detail":{"code":"initial_state_inconsistent","message_en":"…","message_fa":"…"}}
```

---

## 5. Android app

### 5.1 Build

Requirements: JDK 17, Android SDK 34, Gradle 8.7 (wrapper).

```bash
./gradlew :app:assembleDebug
# app/build/outputs/apk/debug/app-debug.apk
```

The debug APK is self-signed and installable directly (`adb install -r`).
A release APK needs your own signing config.

### 5.2 Configure the backend

Settings → **Backend URL**. The default `http://10.0.2.2:8000/` targets an
emulator host; on a phone enter the plant server address, e.g.
`https://platen.plant.local/`. Cleartext HTTP is enabled for commissioning on a
LAN; use HTTPS/WSS outside the plant network.

### 5.3 Screens

1. **Home** — latest saved run, backend health, quick actions.
2. **Steady** — inputs, IF97 prediction, save to history.
3. **Transient** — operating point, time step, initial-condition mode; runs and
   opens the results chart.
4. **Burners** — 24-burner grid (tap toggles, long press edits load/ramp),
   level buttons, live ECharts chart, WebSocket session.
5. **Results** — interactive chart with selectable series, numeric table, CSV and
   PNG export.
6. **History** — Room-backed list, delete, reopen.
7. **About** — fully Persian, RTL, Vazirmatn, formulas and limitations.
8. **Settings** — backend URL, default correlation and default operating point.

RTL: the About screen forces `LayoutDirection.Rtl` and the bundled Vazirmatn font.
Localised error messages are taken from the backend payload.

---

## 6. Tests

```bash
# backend, 76 tests
cd backend && pip install -r requirements.txt && PYTHONPATH=. pytest -q

# android unit tests
./gradlew :app:testDebugUnitTest

# compose UI test (needs a device/emulator)
./gradlew :app:connectedDebugAndroidTest
```

Backend coverage highlights:

* IF97 verification points (regions 1, 2, 4), backward `T(P,h)` inversion.
* Dittus–Boelter and Gnielinski hand calculations at 1e-12 relative tolerance.
* Regime thresholds at exactly 2300 and 10000, transition continuity.
* Spray enthalpy conservation and steady-state outlet within 0.5 °C.
* Energy conservation of the metal node, Euler stability, settling times.
* Three initial-condition modes mutually consistent, drift < 0.01 °C/s.
* Burner layout, ramps, transport delay, four-burner ignition plateau.
* OpenAPI unit-contract scan, REST 422 paths, both WebSocket streams.

---

## 7. Known limitations

* The transient model is deliberately a **single lumped node**; `n_nodes > 1` is
  rejected with a clear error and reserved for Phase 2.
* The Android client needs the backend for prediction; it is not an offline
  calculator (history itself is offline).
* Burner heat distribution uses the constant `q_platen_fraction` and a single gas
  transport delay; no furnace CFD or radiative view factors.
* The seeded "design baseline" run is a representative state, not measured data.
* Turbulent correlations are empirical; `h` is trustworthy in the fully
  turbulent regime and flagged elsewhere.

---

## 8. Disclaimer

Engineering analysis and training tool. It is not a substitute for the plant DCS,
for official operating procedures or for the judgement of the responsible
engineer.
