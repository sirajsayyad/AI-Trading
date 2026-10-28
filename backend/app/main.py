"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db_init import init_db
from app.routers import auth, backtest, coach, dashboard, data, health, replay, risk, trading

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────
    print(f"[START] Starting {settings.app_name} v{settings.app_version}")
    try:
        await init_db()
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
    yield
    # ── Shutdown ─────────────────────────────────────────
    print(f"[STOP] Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Trading Training, Replay & Backtesting Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(data.router)
    app.include_router(backtest.router)
    app.include_router(replay.router)
    app.include_router(coach.router)
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(risk.router)
    app.include_router(trading.router)

    return app


app = create_app()
