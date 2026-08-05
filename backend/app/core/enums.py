from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPPORT = "support"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
