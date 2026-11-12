"""Public practice cases use fictional order references and a separate review scope."""

import threading
import time

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from . import service
from .claims import new_invitation
from .models import Approval, Audit, Case, Evidence, Invitation, Outbox, Proposal
from .practice_access import LIFETIME, PREFIX, issue_practice
from .router import DB
from .schemas import CaseSnapshot

router = APIRouter(tags=["practice"])
MAX_ACTIVE = 100
START_LOCK = threading.Lock()


def clear_expired(db, cutoff: float):
    expired = db.scalars(
        select(Case.id)
        .where(Case.merchant_id.startswith(PREFIX), Case.created_at <= cutoff)
        .order_by(Case.id)
        .with_for_update()
    ).all()
    if not expired:
        return
    proposals = select(Proposal.id).where(Proposal.case_id.in_(expired))
    db.execute(delete(Outbox).where(Outbox.proposal_id.in_(proposals)))
    db.execute(delete(Approval).where(Approval.proposal_id.in_(proposals)))
    for model in (Proposal, Audit, Evidence, Invitation):
        db.execute(delete(model).where(model.case_id.in_(expired)))
    db.execute(delete(Case).where(Case.id.in_(expired)))


@router.post("/api/practice", status_code=201)
def start_practice(db: DB):
    now = int(time.time())
    expires = now + LIFETIME
    token, actor = issue_practice(expires)
    reference = f"PRACTICE-{actor[-12:].upper()}"
    # Local and hosted builds each run one worker. Serialize admissions so
    # concurrent starts cannot both claim the last available practice slot.
    with START_LOCK, db.begin():
        clear_expired(db, now - LIFETIME)
        active = db.scalar(
            select(func.count()).select_from(Case).where(Case.merchant_id.startswith(PREFIX))
        )
        if active >= MAX_ACTIVE:
            raise HTTPException(429, "Practice sessions are full. Please try again later.")
        case = service.create_case(
            db,
            actor,
            CaseSnapshot(
                paypal_order_id=reference, capture_id=reference, amount_minor=4800, currency="USD"
            ),
        )
        path = new_invitation(db, case, expires)
        case_id = case.id
    return {"token": token, "case_id": case_id, "claim_path": path, "expires_at": expires}
