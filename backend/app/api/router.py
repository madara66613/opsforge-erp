from fastapi import APIRouter

from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(audit_logs_router)
