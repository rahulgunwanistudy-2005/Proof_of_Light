"""Durable proposal -> explicit merchant approval -> outbox, in one transaction.

The caller owns the transaction. Nothing here calls PayPal. The executor must
call ready_action again immediately before a sandbox request and hold the case
lock through that request, so a concurrent case edit cannot invalidate approval.
"""

import hashlib
import json
import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import Approval, Audit, Case, Outbox, Proposal
from .schemas import Action, Approve, CaseSnapshot, FinancialAction, Propose


class ReviewError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def case_for_merchant(db: Session, case_id: str, merchant_id: str) -> Case:
    case = db.scalar(
        select(Case).where(Case.id == case_id, Case.merchant_id == merchant_id).with_for_update()
    )
    if case is None:
        raise ReviewError("Case not found", 404)
    return case


def audit(db: Session, case: Case, actor: str, event: str, details: dict):
    previous = db.scalar(
        select(Audit).where(Audit.case_id == case.id).order_by(Audit.sequence.desc()).limit(1)
    )
    prior = previous.entry_hash if previous else "0" * 64
    entry = {
        "case_id": case.id,
        "actor": actor,
        "event": event,
        "details": details,
        "at": time.time(),
    }
    db.add(
        Audit(
            case_id=case.id,
            sequence=previous.sequence + 1 if previous else 1,
            event=entry,
            previous_hash=prior,
            entry_hash=digest({"previous_hash": prior, "event": entry}),
        )
    )
    db.flush()


def create_case(
    db: Session, merchant_id: str, snapshot: CaseSnapshot, *, case_id: str | None = None
) -> Case:
    payload = snapshot.model_dump(mode="json")
    case = Case(merchant_id=merchant_id, inputs_hash=digest(payload), snapshot=payload)
    if case_id is not None:
        case.id = case_id
    db.add(case)
    db.flush()
    audit(db, case, merchant_id, "case_created", {"inputs_hash": case.inputs_hash})
    return case


def revise_case(
    db: Session, case_id: str, merchant_id: str, expected_version: int, snapshot: CaseSnapshot
) -> Case:
    case = case_for_merchant(db, case_id, merchant_id)
    if case.version != expected_version:
        raise ReviewError("The case changed. Refresh it before editing.")
    case.snapshot = snapshot.model_dump(mode="json")
    case.inputs_hash = digest(case.snapshot)
    case.version += 1
    proposal_ids = select(Proposal.id).where(Proposal.case_id == case.id)
    db.execute(
        update(Outbox)
        .where(Outbox.proposal_id.in_(proposal_ids), Outbox.status == "AWAITING_EXECUTOR")
        .values(status="STALE")
    )
    db.execute(
        update(Proposal)
        .where(Proposal.case_id == case.id, Proposal.status.in_(["PENDING_REVIEW", "APPROVED"]))
        .values(status="INVALIDATED")
    )
    audit(
        db,
        case,
        merchant_id,
        "case_updated",
        {"version": case.version, "inputs_hash": case.inputs_hash},
    )
    return case


def validate_action(case: Case, action: FinancialAction):
    snapshot = CaseSnapshot.model_validate(case.snapshot)
    target = snapshot.capture_id if action.action == Action.REFUND_CAPTURE else snapshot.dispute_id
    if not target or action.target_id != target:
        raise ReviewError("The action destination does not match this case.", 422)
    if action.currency != snapshot.currency or action.amount_minor > snapshot.amount_minor:
        raise ReviewError("The amount or currency does not match the recorded purchase.", 422)


def propose(db: Session, case_id: str, merchant_id: str, body: Propose) -> Proposal:
    case = case_for_merchant(db, case_id, merchant_id)
    validate_action(case, body.financial_action)
    # A light-response enum is deliberately never consulted to authorize money
    # or denial. Every proposal, at every amount and severity, requires review.
    payload = body.financial_action.model_dump(mode="json")
    proposal = Proposal(
        case_id=case.id,
        case_version=case.version,
        inputs_hash=case.inputs_hash,
        payload=payload,
        payload_hash=digest(payload),
        rule="explicit_merchant_review_required",
        expires_at=time.time() + 900,
    )
    db.add(proposal)
    db.flush()
    audit(
        db,
        case,
        merchant_id,
        "action_proposed",
        {
            "proposal_id": proposal.id,
            "payload": payload,
            "explanation": body.explanation,
            "requires_approval": True,
        },
    )
    return proposal


def approve(db: Session, proposal_id: str, merchant_id: str, body: Approve) -> Outbox:
    proposal = db.get(Proposal, proposal_id)
    if proposal is None:
        raise ReviewError("Proposal not found", 404)
    case = case_for_merchant(db, proposal.case_id, merchant_id)
    # Refresh after acquiring the case row lock, so concurrent approvals serialize.
    db.refresh(proposal)
    if not body.confirm:
        raise ReviewError("Explicit merchant confirmation is required.", 422)
    if (
        body.expected_payload_hash != proposal.payload_hash
        or body.expected_case_version != case.version
    ):
        raise ReviewError("The proposal changed. Review the latest action before approving.")
    if proposal.case_version != case.version or proposal.inputs_hash != case.inputs_hash:
        raise ReviewError("The case changed. Create and review a new proposal.")
    if proposal.payload_hash != digest(proposal.payload):
        raise ReviewError("The recorded proposal is inconsistent. Create a new proposal.")
    validate_action(case, FinancialAction.model_validate(proposal.payload))
    if proposal.expires_at < time.time():
        raise ReviewError("This proposal expired. Create and review a new proposal.")
    existing = db.scalar(select(Outbox).where(Outbox.proposal_id == proposal.id))
    if existing and proposal.status == "APPROVED":
        return existing  # Repeated browser clicks return the same queued action.
    if proposal.status != "PENDING_REVIEW":
        raise ReviewError("This proposal is no longer available for approval.")
    changed = db.execute(
        update(Proposal)
        .where(Proposal.id == proposal.id, Proposal.status == "PENDING_REVIEW")
        .values(status="APPROVED")
    )
    if changed.rowcount != 1:
        raise ReviewError("This proposal was already reviewed. Refresh the case.")
    approval = Approval(
        proposal_id=proposal.id,
        actor_id=merchant_id,
        payload_hash=proposal.payload_hash,
        inputs_hash=proposal.inputs_hash,
        case_version=case.version,
    )
    db.add(approval)
    db.flush()
    outbox = Outbox(
        proposal_id=proposal.id,
        approval_id=approval.id,
        payload=proposal.payload,
        request_id=digest(
            {
                "case": case.id,
                "proposal": proposal.id,
                "payload_hash": proposal.payload_hash,
                "policy": proposal.policy_version,
            }
        )[:32],
    )
    db.add(outbox)
    db.flush()
    audit(
        db,
        case,
        merchant_id,
        "merchant_approved",
        {
            "proposal_id": proposal.id,
            "approval_id": approval.id,
            "outbox_id": outbox.id,
            "payload_hash": proposal.payload_hash,
        },
    )
    return outbox


def reject(db: Session, proposal_id: str, merchant_id: str, reason: str):
    proposal = db.get(Proposal, proposal_id)
    if proposal is None:
        raise ReviewError("Proposal not found", 404)
    case = case_for_merchant(db, proposal.case_id, merchant_id)
    db.refresh(proposal)
    if proposal.status != "PENDING_REVIEW":
        raise ReviewError("This proposal was already reviewed.")
    proposal.status = "REJECTED"
    audit(
        db, case, merchant_id, "merchant_rejected", {"proposal_id": proposal.id, "reason": reason}
    )


def ready_action(db: Session, outbox_id: str) -> dict:
    """Executor boundary only; checking this function does not send an action."""
    outbox = db.get(Outbox, outbox_id)
    if outbox is None or outbox.status != "AWAITING_EXECUTOR":
        raise ReviewError("Action is not queued for execution.")
    proposal = db.get(Proposal, outbox.proposal_id)
    approval = db.get(Approval, outbox.approval_id)
    if proposal is None or approval is None:
        raise ReviewError("Action lacks its proposal or merchant approval.")
    case = db.scalar(select(Case).where(Case.id == proposal.case_id).with_for_update())
    if case is None:
        raise ReviewError("The source case is missing.")
    db.refresh(proposal)
    db.refresh(outbox)
    if (
        proposal.status != "APPROVED"
        or outbox.status != "AWAITING_EXECUTOR"
        or approval.proposal_id != proposal.id
        or approval.actor_id != case.merchant_id
        or proposal.case_version != case.version
        or approval.case_version != case.version
        or proposal.inputs_hash != case.inputs_hash
        or approval.inputs_hash != case.inputs_hash
        or approval.payload_hash != proposal.payload_hash
        or digest(outbox.payload) != proposal.payload_hash
        or digest(proposal.payload) != proposal.payload_hash
    ):
        raise ReviewError("Approval is stale or does not match this exact action.")
    if proposal.expires_at < time.time():
        raise ReviewError("The approved proposal expired. Request a new review.")
    validate_action(case, FinancialAction.model_validate(outbox.payload))
    return {
        "payload": outbox.payload,
        "request_id": outbox.request_id,
        "approval_id": approval.id,
        "merchant_id": case.merchant_id,
    }
