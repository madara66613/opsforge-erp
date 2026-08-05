from __future__ import annotations

from enum import StrEnum

from app.core.enums import UserRole


class Permission(StrEnum):
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    AUDIT_READ = "audit.read"
    SYSTEM_READ = "system.read"
    DASHBOARD_READ = "dashboard.read"
    PRODUCTS_READ = "products.read"
    PRODUCTS_WRITE = "products.write"
    INVENTORY_READ = "inventory.read"
    INVENTORY_WRITE = "inventory.write"
    INVENTORY_OVERRIDE = "inventory.override"
    PARTNERS_READ = "partners.read"
    PARTNERS_WRITE = "partners.write"
    SALES_READ = "sales.read"
    SALES_WRITE = "sales.write"
    PURCHASES_READ = "purchases.read"
    PURCHASES_WRITE = "purchases.write"
    CSV_IMPORT = "csv.import"
    CSV_EXPORT = "csv.export"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.OPERATOR: frozenset(
        {
            Permission.SYSTEM_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.PRODUCTS_WRITE,
            Permission.INVENTORY_READ,
            Permission.INVENTORY_WRITE,
            Permission.PARTNERS_READ,
            Permission.PARTNERS_WRITE,
            Permission.SALES_READ,
            Permission.SALES_WRITE,
            Permission.PURCHASES_READ,
            Permission.PURCHASES_WRITE,
            Permission.CSV_IMPORT,
            Permission.CSV_EXPORT,
        }
    ),
    UserRole.SUPPORT: frozenset(
        {
            Permission.USERS_READ,
            Permission.AUDIT_READ,
            Permission.SYSTEM_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.INVENTORY_READ,
            Permission.PARTNERS_READ,
            Permission.SALES_READ,
            Permission.PURCHASES_READ,
            Permission.CSV_EXPORT,
        }
    ),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
