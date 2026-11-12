import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import service
from .database import session
from .models import Audit, Case, Outbox, Proposal
from .practice_access import PREFIX, authenticate_practice
from .schemas import Approve, CaseSnapshot, Propose, Reject, StrictModel

router = APIRouter(prefix="/api/review", tags=["merchant review"])
bearer = HTTPBearer(auto_error=False)


Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def merchant(credentials: Credentials) -> str:
    token = os.environ.get("POL_MERCHANT_TOKEN", "")
    actor = os.environ.get("POL_MERCHANT_ID", "")
    if len(token) < 32 or not actor or actor.startswith(PREFIX):
        raise HTTPException(503, "Merchant review is not configured on this server.")
    if (
        not credentials
        or credentials.scheme.lower() != "bearer"
        or not hmac.compare_digest(credentials.credentials.encode(), token.encode())
    ):
        raise HTTPException(
            401,
            "Sign in as the merchant to review financial actions.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return actor


def reviewer(
    credentials: Credentials,
    x_practice_token: Annotated[str | None, Header(max_length=128)] = None,
) -> str:
    if x_practice_token is not None:
        return authenticate_practice(x_practice_token)
    return merchant(credentials)


DB = Annotated[Session, Depends(session)]
Merchant = Annotated[str, Depends(merchant)]
Reviewer = Annotated[str, Depends(reviewer)]


def case_json(case):
    return {
        "id": case.id,
        "version": case.version,
        "inputs_hash": case.inputs_hash,
        "snapshot": case.snapshot,
        "created_at": case.created_at,
    }


def proposal_json(proposal):
    return {
        "id": proposal.id,
        "case_id": proposal.case_id,
        "case_version": proposal.case_version,
        "payload": proposal.payload,
        "payload_hash": proposal.payload_hash,
        "status": proposal.status,
        "rule": proposal.rule,
        "requires_approval": True,
        "expires_at": proposal.expires_at,
    }


@router.get("/cases")
def cases(db: DB, actor: Reviewer):
    return [case_json(case) for case in db.scalars(select(Case).where(Case.merchant_id == actor))]


@router.post("/cases", status_code=201)
def create(body: CaseSnapshot, db: DB, actor: Merchant):
    with db.begin():
        return case_json(service.create_case(db, actor, body))


class Revision(StrictModel):
    expected_version: int = Field(gt=0, strict=True)
    snapshot: CaseSnapshot


@router.put("/cases/{case_id}")
def revise(case_id: str, body: Revision, db: DB, actor: Merchant):
    with db.begin():
        return case_json(
            service.revise_case(db, case_id, actor, body.expected_version, body.snapshot)
        )


@router.get("/cases/{case_id}")
def detail(case_id: str, db: DB, actor: Reviewer):
    case = service.case_for_merchant(db, case_id, actor)
    proposals = db.scalars(select(Proposal).where(Proposal.case_id == case.id)).all()
    actions = db.scalars(
        select(Outbox).where(Outbox.proposal_id.in_([p.id for p in proposals]))
    ).all()
    audit = db.scalars(select(Audit).where(Audit.case_id == case.id).order_by(Audit.sequence)).all()
    return {
        **case_json(case),
        "proposals": [proposal_json(p) for p in proposals],
        "actions": [
            {
                "id": a.id,
                "status": a.status,
                "payload": a.payload,
                "request_id": a.request_id,
                "paypal_executed": a.status == "COMPLETED",
                "provider_result": a.provider_result,
            }
            for a in actions
        ],
        "audit": [
            {
                "sequence": a.sequence,
                "event": a.event,
                "previous_hash": a.previous_hash,
                "entry_hash": a.entry_hash,
            }
            for a in audit
        ],
    }


@router.post("/cases/{case_id}/proposals", status_code=201)
def propose(case_id: str, body: Propose, db: DB, actor: Reviewer):
    with db.begin():
        return proposal_json(service.propose(db, case_id, actor, body))


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: str, body: Approve, db: DB, actor: Reviewer):
    with db.begin():
        action = service.approve(db, proposal_id, actor, body)
        return {
            "outbox_id": action.id,
            "status": action.status,
            "request_id": action.request_id,
            "paypal_executed": False,
            "message": (
                "Practice approval saved."
                if actor.startswith(PREFIX)
                else "Approval saved. Review the action before sending it to PayPal."
            ),
        }


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: str, body: Reject, db: DB, actor: Reviewer):
    with db.begin():
        service.reject(db, proposal_id, actor, body.reason)
    return {"status": "REJECTED", "paypal_executed": False}
