"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import APP_VERSION
from app.api import (
    routes_burner,
    routes_calibration,
    routes_htc,
    routes_properties,
    routes_runs,
    routes_steady,
    routes_transient,
    websocket,
)
from app.core.config import settings
from app.core.errors import DomainError
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import RateLimitMiddleware
from app.db.models import RunStore
from app.db.session import Database
from app.models.schemas import HealthResponse
from app.thermo import if97
from app.thermo.geometry import DEFAULT_GEOMETRY

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the database, seed the baseline run and attach the run store."""
    configure_logging()
    database = Database(settings.resolved_db_path())
    database.init_schema()
    store = RunStore(database)
    store.ensure_baseline()
    app.state.database = database
    app.state.store = store
    logger.info(
        "startup",
        extra={
            "version": APP_VERSION,
            "db": str(database.path),
            "n_tubes": DEFAULT_GEOMETRY.n_tubes,
        },
    )
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    """Build the ASGI application."""
    app = FastAPI(
        title="Platen Superheater Digital Twin",
        version=APP_VERSION,
        description=(
            "IAPWS-IF97 steady, transient and graphical burner start/stop model of the "
            "platen superheater of a 325 MW natural-circulation boiler. "
            "All payload values use t/h, \u00b0C, bar, MW and W/m\u00b2K."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("domain_error", extra={"code": exc.code, "context": exc.context})
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_payload()})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message_en": "Request validation failed.",
                    "message_fa": "\u0627\u0639\u062a\u0628\u0627\u0631\u0633\u0646\u062c\u06cc \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0646\u0627\u0645\u0648\u0641\u0642 \u0628\u0648\u062f.",
                    "context": {"errors": exc.errors()},
                }
            },
        )

    for module in (
        routes_steady,
        routes_transient,
        routes_burner,
        routes_properties,
        routes_htc,
        routes_calibration,
        routes_runs,
        websocket,
    ):
        app.include_router(module.router)

    @app.get("/api/health", response_model=HealthResponse, tags=["meta"])
    def health() -> dict:
        """Liveness probe."""
        return {
            "status": "ok",
            "version": APP_VERSION,
            "if97": "iapws-1.5.x (IAPWS-IF97 + IAPWS 2008 viscosity + IAPWS 2011 conductivity)",
        }

    @app.get("/api/geometry", tags=["meta"])
    def geometry() -> dict:
        """Frozen platen geometry and derived thermal capacitance."""
        return DEFAULT_GEOMETRY.as_dict()

    @app.get("/api/saturation", tags=["meta"])
    def saturation(P_bar: float) -> dict:
        """Saturation temperature at a pressure."""
        return {"P_bar": P_bar, "T_sat_C": if97.tsat_p(P_bar), "h_f_kJ_kg": if97.sat_liquid_h(P_bar)}

    return app


app = create_app()
