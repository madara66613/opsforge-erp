from fastapi import APIRouter

from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.orders import router as orders_router
from app.api.routes.partners import router as partners_router
from app.api.routes.products import router as products_router
from app.api.routes.users import router as users_router
from app.api.routes.warehouses import router as warehouses_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(audit_logs_router)
api_router.include_router(products_router)
api_router.include_router(warehouses_router)
api_router.include_router(inventory_router)
api_router.include_router(partners_router)
api_router.include_router(orders_router)
api_router.include_router(dashboard_router)
