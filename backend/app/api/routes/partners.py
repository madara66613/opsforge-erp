from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.enums import AuditOutcome, PartnerType
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.partner import Partner
from app.schemas.partner import PartnerCreate, PartnerList, PartnerPublic, PartnerUpdate
from app.services.audit import record_audit_event

router = APIRouter(prefix="/partners", tags=["partners"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CanReadPartners = Annotated[AuthContext, Depends(require_permission(Permission.PARTNERS_READ))]
CanWritePartners = Annotated[AuthContext, Depends(require_permission(Permission.PARTNERS_WRITE))]


@router.get("", response_model=PartnerList)
def list_partners(
    session: DatabaseSession,
    _auth: CanReadPartners,
    search: str | None = None,
    partner_type: PartnerType | None = None,
    active: bool | None = None,
    sort_by: Literal["code", "name", "partner_type", "created_at"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PartnerList:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Partner.code.ilike(pattern),
                Partner.name.ilike(pattern),
                Partner.tax_id.ilike(pattern),
            )
        )
    if partner_type:
        filters.append(Partner.partner_type == partner_type)
    if active is not None:
        filters.append(Partner.is_active == active)

    total = session.scalar(select(func.count()).select_from(Partner).where(*filters)) or 0
    sort_columns = {
        "code": Partner.code,
        "name": Partner.name,
        "partner_type": Partner.partner_type,
        "created_at": Partner.created_at,
    }
    direction = asc if sort_order == "asc" else desc
    partners = list(
        session.scalars(
            select(Partner)
            .where(*filters)
            .order_by(direction(sort_columns[sort_by]), Partner.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return PartnerList(
        items=[PartnerPublic.model_validate(partner) for partner in partners],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PartnerPublic, status_code=status.HTTP_201_CREATED)
def create_partner(
    payload: PartnerCreate,
    request: Request,
    session: DatabaseSession,
    auth: CanWritePartners,
) -> PartnerPublic:
    actor_id = auth.user.id
    partner = Partner(**payload.model_dump(mode="python"))
    session.add(partner)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="partner.create",
            entity_type="partner",
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "code_already_exists", "code": payload.code},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A partner with this code already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="partner.create",
        entity_type="partner",
        entity_id=str(partner.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"code": partner.code, "partner_type": partner.partner_type.value},
    )
    session.commit()
    return PartnerPublic.model_validate(partner)


@router.get("/{partner_id}", response_model=PartnerPublic)
def get_partner(
    partner_id: UUID,
    session: DatabaseSession,
    _auth: CanReadPartners,
) -> PartnerPublic:
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerPublic.model_validate(partner)


@router.patch("/{partner_id}", response_model=PartnerPublic)
def update_partner(
    partner_id: UUID,
    payload: PartnerUpdate,
    request: Request,
    session: DatabaseSession,
    auth: CanWritePartners,
) -> PartnerPublic:
    actor_id = auth.user.id
    partner = session.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partner not found")

    updates = payload.model_dump(exclude_unset=True, mode="python")
    nullable_fields = {"email", "phone", "address", "tax_id"}
    for field_name, value in updates.items():
        if field_name in nullable_fields or value is not None:
            setattr(partner, field_name, value)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        record_audit_event(
            session,
            actor_user_id=actor_id,
            action="partner.update",
            entity_type="partner",
            entity_id=str(partner_id),
            outcome=AuditOutcome.FAILURE,
            request_id=request.state.request_id,
            details={"reason": "code_already_exists"},
        )
        session.commit()
        raise HTTPException(
            status_code=409, detail="A partner with this code already exists"
        ) from exc

    record_audit_event(
        session,
        actor_user_id=actor_id,
        action="partner.update",
        entity_type="partner",
        entity_id=str(partner.id),
        outcome=AuditOutcome.SUCCESS,
        request_id=request.state.request_id,
        details={"changed_fields": sorted(updates)},
    )
    session.commit()
    return PartnerPublic.model_validate(partner)
