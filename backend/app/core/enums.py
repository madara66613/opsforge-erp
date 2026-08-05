from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPPORT = "support"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class StockMovementType(StrEnum):
    RECEIPT = "receipt"
    SALE_ISSUE = "sale_issue"
    TRANSFER = "transfer"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


class PartnerType(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class SalesOrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"
