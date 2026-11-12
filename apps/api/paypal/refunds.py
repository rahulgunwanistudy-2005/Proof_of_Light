"""Explicit merchant dispatch of one approved sandbox capture refund."""

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from apps.api.review import service
from apps.api.review.models import Outbox, Proposal
from apps.api.review.router import DB, Merchant
from apps.api.review.schemas import Action

from .checkout import PayPalFailure
from .shop import Client, router


@router.post("/api/review/actions/{action_id}/send")
def send(action_id: str, db: DB, actor: Merchant, paypal: Client):
    with db.begin():
        row = db.get(Outbox, action_id)
        proposal = db.get(Proposal, row.proposal_id) if row else None
        if proposal is None:
            raise HTTPException(404, "Approved action not found.")
        case = service.case_for_merchant(db, proposal.case_id, actor)
        authorized = service.ready_action(db, action_id)
        payload = authorized["payload"]
        if payload["action"] != Action.REFUND_CAPTURE or payload["currency"] != "USD":
            raise HTTPException(
                422, "This integration sends USD capture refunds. Handle other actions in PayPal."
            )
        if case.snapshot.get("dispute_id"):
            raise HTTPException(409, "Review disputed payments in PayPal’s Resolution Center.")
        capture_id = payload["target_id"]
        try:
            order = paypal.get_order(case.snapshot["paypal_order_id"]).data
        except ValueError as exc:
            raise HTTPException(
                422, "Use the order ID from an actual PayPal sandbox purchase."
            ) from exc
        captures = [
            capture
            for unit in order.get("purchase_units", [])
            for capture in unit.get("payments", {}).get("captures", [])
        ]
        capture = next((item for item in captures if item.get("id") == capture_id), {})
        amount = capture.get("amount", {})
        try:
            verified_minor = Decimal(amount.get("value", "0")) * 100
        except InvalidOperation:
            verified_minor = 0
        if (
            order.get("id") != case.snapshot["paypal_order_id"]
            or capture.get("status") != "COMPLETED"
            or amount.get("currency_code") != payload["currency"]
            or verified_minor != case.snapshot["amount_minor"]
        ):
            raise HTTPException(
                409, "PayPal could not verify an unrefunded capture matching this case."
            )
        # A guarded write also takes SQLite's write lock before the external call.
        try:
            claimed = db.execute(
                update(Outbox)
                .where(Outbox.id == row.id, Outbox.status == "AWAITING_EXECUTOR")
                .values(attempts=Outbox.attempts + 1, refund_capture_id=capture_id)
            )
        except IntegrityError as exc:
            raise HTTPException(
                409, "This capture already has a refund attempt. Check its status in PayPal."
            ) from exc
        if claimed.rowcount != 1:
            raise HTTPException(409, "The action changed. Refresh the case.")
        # Recheck expiry and the approval after acquiring the database write lock.
        service.ready_action(db, action_id)
        try:
            result = paypal.refund(
                capture_id, payload["amount_minor"], payload["currency"], authorized["request_id"]
            )
        except PayPalFailure as error:
            # Treat an interrupted send as unresolved. The request ID remains
            # available for reconciliation in PayPal. Do not create a new key.
            row.status = (
                "RECONCILE" if error.status is None or error.status >= 500 else "PROVIDER_REJECTED"
            )
            row.provider_result = {
                "debug_id": error.debug_id,
                "http_status": error.status,
                "kind": error.kind,
            }
        else:
            state = result.data.get("status")
            refund_id = result.data.get("id")
            if state == "COMPLETED" and refund_id:
                row.status = "COMPLETED"
            elif state == "PENDING" and refund_id:
                row.status = "PAYPAL_PENDING"
            else:
                row.status = "RECONCILE"
            row.provider_result = {
                "refund_id": refund_id,
                "paypal_status": state,
                "debug_id": result.debug_id,
            }
        service.audit(
            db,
            case,
            actor,
            "paypal_refund_response",
            {"outbox_id": row.id, "status": row.status, "provider_result": row.provider_result},
        )
        return {
            "outbox_id": row.id,
            "status": row.status,
            "provider_result": row.provider_result,
            "paypal_executed": row.status == "COMPLETED",
        }
