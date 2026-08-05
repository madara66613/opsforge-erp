from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import AuditOutcome, StockMovementType, UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.inventory import InventoryBalance, StockMovement
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse


@dataclass(frozen=True)
class DemoUser:
    id: UUID
    email: str
    full_name: str
    role: UserRole
    password: str


DEMO_USERS = (
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        email="admin@demo.opsforge.dev",
        full_name="Alex Morgan",
        role=UserRole.ADMIN,
        password="AdminDemo!2026",
    ),
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000002"),
        email="operator@demo.opsforge.dev",
        full_name="Olivia Chen",
        role=UserRole.OPERATOR,
        password="OperatorDemo!2026",
    ),
    DemoUser(
        id=UUID("10000000-0000-0000-0000-000000000003"),
        email="support@demo.opsforge.dev",
        full_name="Sam Rivera",
        role=UserRole.SUPPORT,
        password="SupportDemo!2026",
    ),
)


@dataclass(frozen=True)
class DemoProduct:
    id: UUID
    sku: str
    name: str
    unit: str
    sale_price: Decimal
    purchase_price: Decimal


@dataclass(frozen=True)
class DemoWarehouse:
    id: UUID
    code: str
    name: str
    location: str


DEMO_PRODUCTS = (
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000001"),
        "SCN-200",
        "Orbit barcode scanner",
        "pcs",
        Decimal("449.00"),
        Decimal("298.00"),
    ),
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000002"),
        "PRN-420",
        "Forge thermal label printer",
        "pcs",
        Decimal("899.00"),
        Decimal("645.00"),
    ),
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000003"),
        "TBL-10",
        "Field rugged tablet 10",
        "pcs",
        Decimal("2499.00"),
        Decimal("1875.00"),
    ),
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000004"),
        "CAB-USBC-2M",
        "USB-C reinforced cable 2m",
        "pcs",
        Decimal("49.90"),
        Decimal("21.50"),
    ),
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000005"),
        "RTR-AX600",
        "Mesh office router AX600",
        "pcs",
        Decimal("679.00"),
        Decimal("462.00"),
    ),
    DemoProduct(
        UUID("20000000-0000-0000-0000-000000000006"),
        "TON-BLK-55",
        "Black toner cartridge 55",
        "pcs",
        Decimal("329.00"),
        Decimal("214.00"),
    ),
)


DEMO_WAREHOUSES = (
    DemoWarehouse(
        UUID("30000000-0000-0000-0000-000000000001"),
        "WAW-CENTRAL",
        "Warsaw central warehouse",
        "Warsaw, Masovian",
    ),
    DemoWarehouse(
        UUID("30000000-0000-0000-0000-000000000002"),
        "POZ-WEST",
        "Poznan west warehouse",
        "Poznan, Greater Poland",
    ),
)


OPENING_QUANTITIES: dict[tuple[str, str], Decimal] = {
    ("SCN-200", "WAW-CENTRAL"): Decimal("24"),
    ("SCN-200", "POZ-WEST"): Decimal("8"),
    ("PRN-420", "WAW-CENTRAL"): Decimal("12"),
    ("PRN-420", "POZ-WEST"): Decimal("5"),
    ("TBL-10", "WAW-CENTRAL"): Decimal("7"),
    ("TBL-10", "POZ-WEST"): Decimal("2"),
    ("CAB-USBC-2M", "WAW-CENTRAL"): Decimal("180"),
    ("CAB-USBC-2M", "POZ-WEST"): Decimal("75"),
    ("RTR-AX600", "WAW-CENTRAL"): Decimal("16"),
    ("RTR-AX600", "POZ-WEST"): Decimal("6"),
    ("TON-BLK-55", "WAW-CENTRAL"): Decimal("36"),
    ("TON-BLK-55", "POZ-WEST"): Decimal("14"),
}


def seed_demo_users() -> None:
    settings = get_settings()
    if settings.environment not in {"local", "test"}:
        raise RuntimeError("Demo data can only be seeded in local or test environments")

    with SessionLocal() as session:
        for demo_user in DEMO_USERS:
            existing = session.scalar(select(User).where(User.email == demo_user.email))
            if existing is None:
                session.add(
                    User(
                        id=demo_user.id,
                        email=demo_user.email,
                        full_name=demo_user.full_name,
                        role=demo_user.role,
                        password_hash=hash_password(demo_user.password),
                        is_active=True,
                    )
                )
        session.commit()


def seed_demo_inventory() -> None:
    settings = get_settings()
    if settings.environment not in {"local", "test"}:
        raise RuntimeError("Demo data can only be seeded in local or test environments")

    with SessionLocal() as session:
        admin = session.get(User, DEMO_USERS[0].id)
        if admin is None:
            raise RuntimeError("Seed demo users before inventory")

        warehouse_by_code: dict[str, Warehouse] = {}
        for demo_warehouse in DEMO_WAREHOUSES:
            warehouse = session.scalar(
                select(Warehouse).where(Warehouse.code == demo_warehouse.code)
            )
            if warehouse is None:
                warehouse = Warehouse(
                    id=demo_warehouse.id,
                    code=demo_warehouse.code,
                    name=demo_warehouse.name,
                    location=demo_warehouse.location,
                    is_active=True,
                )
                session.add(warehouse)
            warehouse_by_code[warehouse.code] = warehouse

        product_by_sku: dict[str, Product] = {}
        for demo_product in DEMO_PRODUCTS:
            product = session.scalar(select(Product).where(Product.sku == demo_product.sku))
            if product is None:
                product = Product(
                    id=demo_product.id,
                    sku=demo_product.sku,
                    name=demo_product.name,
                    unit=demo_product.unit,
                    sale_price=demo_product.sale_price,
                    purchase_price=demo_product.purchase_price,
                    is_active=True,
                )
                session.add(product)
            product_by_sku[product.sku] = product
        session.flush()

        movement_sequence = 1
        for (sku, warehouse_code), quantity in OPENING_QUANTITIES.items():
            product = product_by_sku[sku]
            warehouse = warehouse_by_code[warehouse_code]
            balance = session.scalar(
                select(InventoryBalance).where(
                    InventoryBalance.product_id == product.id,
                    InventoryBalance.warehouse_id == warehouse.id,
                )
            )
            reference = f"SEED-OPENING-{sku}-{warehouse_code}"
            movement_exists = session.scalar(
                select(StockMovement.id).where(StockMovement.reference == reference)
            )
            if balance is None:
                balance = InventoryBalance(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    quantity=quantity,
                )
                session.add(balance)
            if movement_exists is None:
                session.add(
                    StockMovement(
                        id=UUID(f"40000000-0000-0000-0000-{movement_sequence:012d}"),
                        movement_type=StockMovementType.RECEIPT,
                        product_id=product.id,
                        warehouse_id=warehouse.id,
                        quantity=quantity,
                        unit_cost=product.purchase_price,
                        reference=reference,
                        notes="Deterministic local demo opening balance",
                        created_by_user_id=admin.id,
                    )
                )
            movement_sequence += 1

        seed_audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "demo.seed",
                AuditLog.entity_id == "inventory-v1",
            )
        )
        if seed_audit is None:
            session.add(
                AuditLog(
                    id=UUID("50000000-0000-0000-0000-000000000001"),
                    actor_user_id=admin.id,
                    action="demo.seed",
                    entity_type="system",
                    entity_id="inventory-v1",
                    outcome=AuditOutcome.SUCCESS,
                    details={"products": len(DEMO_PRODUCTS), "warehouses": len(DEMO_WAREHOUSES)},
                )
            )
        session.commit()


if __name__ == "__main__":
    seed_demo_users()
    seed_demo_inventory()
    print("Seeded OpsForge ERP demo users and inventory.")
