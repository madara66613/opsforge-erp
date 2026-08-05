from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyRecord
from app.services.errors import DomainError


def request_fingerprint(operation: str, resource_id: UUID) -> str:
    return hashlib.sha256(f"{operation}:{resource_id}".encode()).hexdigest()


def claim_or_replay(
    session: Session,
    *,
    operation: str,
    idempotency_key: str,
    resource_id: UUID,
    actor_user_id: UUID,
) -> bool:
    fingerprint = request_fingerprint(operation, resource_id)
    existing = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.resource_id != resource_id or existing.request_hash != fingerprint:
            raise DomainError(
                "Idempotency key was already used for a different resource",
                code="idempotency_key_conflict",
            )
        return True

    session.add(
        IdempotencyRecord(
            operation=operation,
            idempotency_key=idempotency_key,
            resource_id=resource_id,
            request_hash=fingerprint,
            actor_user_id=actor_user_id,
        )
    )
    session.flush()
    return False
