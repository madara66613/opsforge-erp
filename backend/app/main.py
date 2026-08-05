from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.system import router as system_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="OpsForge ERP API",
    summary="Operational ERP API for a fictional small distributor",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(system_router)
app.include_router(api_router, prefix="/api/v1")
