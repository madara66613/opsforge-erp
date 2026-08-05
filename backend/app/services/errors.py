from __future__ import annotations

from typing import Any


class DomainError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 409,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundError(DomainError):
    def __init__(self, entity: str) -> None:
        super().__init__(
            f"{entity} not found",
            code=f"{entity.lower().replace(' ', '_')}_not_found",
            status_code=404,
        )
