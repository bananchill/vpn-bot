"""FastAPI application entry point.

Configures CORS, lifespan (bot polling as background task), health endpoint,
and includes all API routers.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from api.router_configs import router as configs_router
from api.router_dashboard import router as dashboard_router
from api.router_logs import router as logs_router
from api.router_promos import router as promos_router
from api.router_settings import router as settings_router
from api.router_users import router as users_router
from bot.bot import start_polling, stop_polling
from config import WEBAPP_URL
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    Launches the aiogram bot polling as a background task so that the
    FastAPI server and Telegram bot run concurrently in the same process.
    """
    logger.info("Starting application lifespan")
    polling_task = asyncio.create_task(start_polling())

    yield

    logger.info("Shutting down application lifespan")
    await stop_polling()
    polling_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await polling_task


app = FastAPI(
    title="Admin Mini App API",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from the Mini App frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEBAPP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(settings_router)
app.include_router(users_router)
app.include_router(configs_router)
app.include_router(dashboard_router)
app.include_router(promos_router)
app.include_router(logs_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Lightweight health check endpoint."""
    return {"status": "ok"}
