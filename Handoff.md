# Platen Superheater Digital Twin v4.0.0 — Project Hand-off

---

## Repository Context

- **GitHub:** `mohsenRahimi1708/SteamMixerCalculatorPythonV01`
- **Starting branch:** `main` (v3 Chaquopy engine) — **untouched**
- **New branch:** `feature/v4.0.0-platen-superheater-twin` ✅ created and pushed
- **Current HEAD:** commit `75deddc` on the new branch

## Version

| Item | Value |
| --- | --- |
| **versionCode** | `4` (Android) |
| **versionName** | `4.0.0` |
| **semantic** | `4.0.0` (major feature change) |

## What v4 replaces

| Aspect | v3 (on previous `main`) | v4 |
| --- | --- | --- |
| Physics engine | Chaquopy Python **inside** the APK | FastAPI service (single source of truth) |
| Property library | `pyXSteam` wrapper | IAPWS‑IF97 (`iapws` Python 1.5.5) + IAPWS 2008/2011 correlations |
| Screens | 3 (spray, impact, transient) | **8** (home, steady, transient, burners, results, history, about, settings) |
| Heat transfer | constant / not modelled | dynamic `h(t)` from `Re`, `Pr`, regime‑aware `Nu` (Dittus‑Boelter and Gnielinski) |
| Burner model | number of burners only | 24 tagged burners, per‑burner load & ramp, graphical ignition |
| Charts | static Compose canvas | interactive **ECharts** in a WebView |
| History | none | **Room** (device) + **SQLite** (server) |
| Persian support | none | full RTL About screen, bilingual error messages |

## Units (enforced end‑to‑end)

| Quantity | Unit |
| --- | --- |
| Mass flow | **t/h** |
| Temperature | **°C** |
| Pressure | **bar** |
| Heat rate | **MW** |
| Heat transfer coefficient | **W/m²K** |

SI units (kg/s, K, Pa) appear **only inside the Python solver**; the API and UI always use the four contractual units.

## Backend (`backend/`)

- **FastAPI + Uvicorn** on port 8000
- **IAPWS‑IF97** for all steam‑table look‑ups (backward `T(P,h)` inversion, viscosity, conductivity)
- **HTC** via Gnielinski and Dittus‑Boelter, with laminar/turbulent transition
- **Spray mixing**, **steady solver**, **single‑node transient** with sub‑stepping
- **24‑burner schedule** with transport lag `gas_to_metal_lag_s = 5 s`
- **WebSocket streams** `/ws/transient` and `/ws/burner_startup`
- **SQLite run store** (Room on the Android client mirrors it)
- **76 tests** passing (`pytest -q`, 100 % unit‑test coverage on the model contract)
- **Docker** (`docker compose up --build`) includes nginx reverse proxy with TLS and WSS upgrade
- **OpenAPI schema** with unit‑contract scan (fails if kg/s, Pa‑family, or K appear)

### Key Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/steady` | steady‑state platen prediction |
| POST | `/api/transient` | single‑node transient series |
| POST | `/api/burner_startup` | burner schedule simulation |
| GET | `/api/properties` | IF97 state point |
| GET | `/api/htc` | heat‑transfer diagnostics |
| POST | `/api/calibrate` | least‑squares `Q_platen` fit |
| GET/POST/DELETE | `/api/runs` | server‑side history |
| GET | `/api/health` / `/api/geometry` | service and geometry |
| WSS | `/ws/transient` | frame‑by‑frame replay of a transient |
| WSS | `/ws/burner_startup` | live burner session + `set_burner` commands |

### Docker / Production

```bash
cd backend
docker compose up --build -d      # http://localhost:8080
# For TLS: mount platensh.crt/key into backend/deploy/certs, use 8443 listener
```

### Run Locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

## Android App (`app/`)

- **Kotlin + Jetpack Compose + Material 3 + RTL‑aware**
- **Hilt** for DI, **Room** for local SQLite history
- **Retrofit 2.11** + **OkHttp** for REST, **OkHttpWebSocket** for WSS
- **ksp** + **ksp‑hilt‑android** plugin (AGP 8.5.2, Kotlin 2.0.21)
- **Vazirmatn** TTF bundled (Persian RTL throughout)
- **Apache ECharts 1.0.3** in a WebView for interactive charts
- **8 full screens** (see below)

### Screens

| # | Screen | Key Features |
|---|--------|--------------|
| 1 | **Home** | latest saved run, backend health, quick actions |
| 2 | **Steady** | inputs, IF97 prediction, save to history |
| 3 | **Transient** | operating point, time step, initial‑condition mode; opens results chart |
| 4 | **Burners** | 24‑burner grid (tap toggles, long press edits load/ramp), level buttons, live ECharts chart, WebSocket session (`set_burner` commands) |
| 5 | **Results** | interactive chart with selectable series, numeric table, **CSV & PNG export** |
| 6 | **History** | Room‑backed list, delete, reopen to results |
| 7 | **About** | **fully Persian, RTL**, Vazirmatn font, formulas and limitations |
| 8 | **Settings** | backend URL, default HTC correlation, default operating point |

### Build & Install

```bash
# From the repo root
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
# Install: adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The debug APK is signed with the default debug keystore. A release APK requires your own `signingConfigs`.

### Default Backend URL

Settings → **Backend URL**. The default `http://10.0.2.2:8000/` targets an emulator host; on a physical phone enter the plant server address, e.g. `https://platen.plant.local/`. Cleartext HTTP is enabled for commissioning on a LAN; use HTTPS/WSS outside the plant network.

### Git Branch

```
git branch --show-current   → feature/v4.0.0-platen-superheater-twin
git log --oneline -1        → 75deddc feat: platen superheater digital twin with FastAPI backend (v4.0.0)
```

The commit is **already pushed** to GitHub:
```
https://github.com/mohsenRahimi1708/SteamMixerCalculatorPythonV01/pull/new/feature/v4.0.0-platen-superheater-twin
```

## Documentation (Markdown)

| File | Content |
| --- | --- |
| `README.md` | English overview: version, unit contract, physics, backend endpoints, Android build, tests, limitations, disclaimer |
| `README_fa.md` | Persian‑RTL overview of the same material |
| `backend/README.md` | Compact backend layout, commands, design notes |
| `dist/platen-twin-v4.0.0-debug.apk` | SHA‑256 `5d207190dfb1111691bb57fc66ad8db3d65b212a4c1305d82430a31902c1abe5` |

## Checks Actually Run

| Check | Result |
| --- | --- |
| `./gradlew :app:assembleDebug` | **BUILD SUCCESSFUL** — 18 MB APK produced |
| `./gradlew :app:testDebugUnitTest :app:compileDebugAndroidTestKotlin` | **exit 0** — JVM unit tests pass, Compose test compiles |
| `pytest -q` (backend) | **exit 0** — 76 tests passing |
| `aapt dump badging` (APK) | `versionCode='4'`, `versionName='4.0.0'`, `package='com.steamcalc'` |
| Compose UI test on device | **not run** (requires a physical device or emulator; live backend connection unverified) |

## Known Limitations (from the docs)

- Transient model is a **single lumped node**; `N > 1` is rejected with a clear error (Phase 2 later).
- Android client needs the backend for prediction; only history works offline.
- Burner heat distribution uses a constant `q_platen_fraction` and a single gas transport delay; no furnace CFD.
- Turbulent correlations are empirical; `h` is trustworthy only in the fully turbulent regime.
- Seeded “design baseline” run is a representative state, not measured data.

## What Still Needs Doing (next steps you may wish to take)

1. **Open the PR** on GitHub from `feature/v4.0.0-platen-superheater-twin` → `main`.
2. **Add release signing** and produce a signed release APK.
3. **Install on an emulator or device**, start the backend, and exercise the steady/transient/Burner screens against the live API.
4. **Run the Compose UI tests** on a device/emulator to verify the full navigation flow.

## Author Identity

```
git config --global user.email "mrmr1708@gmail.com"
git config --global user.name "mohsen rahimi"
```

Already set in the repo history; the commit footer uses `mohsen rahimi <mrmr1708@gmail.com>`.

---

**You now have a complete, buildable Android app (debug APK delivered) and a full‑featured FastAPI backend, all on a new branch with version 4.0.0.**