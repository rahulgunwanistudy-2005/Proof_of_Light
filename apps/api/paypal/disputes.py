"""Read-only PayPal dispute import and verified webhook refresh."""

import os
import re
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlsplit

import requests
from fastapi import HTTPException, Request
from sqlalchemy import select

from apps.api.review import service
from apps.api.review.models import Case, CheckoutOrder
from apps.api.review.router import DB, Merchant
from apps.api.review.schemas import CaseSnapshot

from .checkout import PayPalFailure, debug_id
from .shop import Client, router

BASE = "https://api-m.sandbox.paypal.com"
DISPUTE_PATH = "/v1/customer/disputes"


def rest(paypal, path, *, params=None, body=None):
    # OAuth callback and SDK calls share the same in-process token and lock.
    try:
        token = paypal.access_token()
        result = requests.request(
            "GET" if body is None else "POST",
            BASE + path,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            json=body,
            timeout=15,
            allow_redirects=False,
        )
        if result.status_code != 200:
            raise PayPalFailure(
                "paypal_rejected_request", result.status_code, debug_id(result.headers)
            )
        return result.json()
    except (requests.RequestException, ValueError) as exc:
        raise PayPalFailure("paypal_dispute_request_failed") from exc


def summary(raw):
    return {
        "id": raw.get("dispute_id"),
        "reason": raw.get("reason"),
        "status": raw.get("status"),
        "stage": raw.get("dispute_life_cycle_stage"),
        "updated_at": raw.get("update_time"),
        "seller_due": raw.get("seller_response_due_date"),
        "amount": raw.get("dispute_amount", {}),
    }


@router.get("/api/review/disputes")
def disputes(actor: Merchant, paypal: Client):
    items, seen = [], set()
    token = None
    for _ in range(5):
        params = {"page_size": 20}
        if token:
            params["next_page_token"] = token
        data = rest(paypal, DISPUTE_PATH, params=params)
        items.extend(summary(item) for item in data.get("items", []))
        link = next(
            (item.get("href", "") for item in data.get("links", []) if item.get("rel") == "next"),
            "",
        )
        token = parse_qs(urlsplit(link).query).get("next_page_token", [None])[0]
        if not token or token in seen:
            break
        seen.add(token)
    return items


def dispute_detail(paypal, dispute_id):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", dispute_id):
        raise HTTPException(422, "Enter a valid PayPal dispute ID.")
    raw = rest(paypal, f"{DISPUTE_PATH}/{dispute_id}")
    if raw.get("dispute_id") != dispute_id:
        raise HTTPException(502, "PayPal returned a different dispute.")
    return raw


def existing_case(db, actor, dispute_id):
    return db.scalar(
        select(Case)
        .where(Case.merchant_id == actor, Case.snapshot["dispute_id"].as_string() == dispute_id)
        .order_by(Case.created_at)
        .limit(1)
        .with_for_update()
    )


def refresh_case(db, case, raw):
    snapshot = CaseSnapshot.model_validate(case.snapshot)
    details = summary(raw)
    if snapshot.provider_dispute != details:
        service.revise_case(
            db,
            case.id,
            case.merchant_id,
            case.version,
            snapshot.model_copy(update={"provider_dispute": details}),
        )


def save_dispute(db, actor: str, raw: dict):
    dispute_id = raw["dispute_id"]
    amount = raw.get("dispute_amount", {})
    try:
        minor = Decimal(amount.get("value", "")) * 100
        if (
            amount.get("currency_code") != "USD"
            or not 0 < minor <= 100_000_000
            or minor != int(minor)
        ):
            raise ValueError
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise HTTPException(422, "Dispute import currently supports USD amounts.") from exc
    capture_ids = [
        entry.get("seller_transaction_id")
        for entry in raw.get("disputed_transactions", [])
        if entry.get("seller_transaction_id")
    ]
    case = existing_case(db, actor, dispute_id)
    if case:
        refresh_case(db, case, raw)
        return {"id": case.id}
    order = db.scalar(
        select(CheckoutOrder)
        .where(
            CheckoutOrder.merchant_id == actor,
            CheckoutOrder.capture_id.in_(capture_ids),
            CheckoutOrder.status == "COMPLETED",
        )
        .limit(1)
    )
    case = service.create_case(
        db,
        actor,
        CaseSnapshot(
            paypal_order_id=order.paypal_id if order else "PayPal dispute",
            capture_id=order.capture_id if order else None,
            dispute_id=dispute_id,
            amount_minor=order.amount_minor if order else int(minor),
            currency="USD",
            provider_dispute=summary(raw),
            shipment=(order.tracking or {}) if order else {},
        ),
        case_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"proof-of-light:paypal:{actor}:{dispute_id}")),
    )
    return {"id": case.id}


@router.post("/api/review/disputes/{dispute_id}/import")
def import_dispute(dispute_id: str, db: DB, actor: Merchant, paypal: Client):
    raw = dispute_detail(paypal, dispute_id)
    with db.begin():
        return save_dispute(db, actor, raw)


@router.post("/api/paypal/webhooks")
def webhook(event: dict, request: Request, db: DB, paypal: Client):
    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID")
    if not webhook_id:
        raise HTTPException(503, "PayPal webhook verification is not configured.")
    header_names = {
        "auth_algo": "paypal-auth-algo",
        "cert_url": "paypal-cert-url",
        "transmission_id": "paypal-transmission-id",
        "transmission_sig": "paypal-transmission-sig",
        "transmission_time": "paypal-transmission-time",
    }
    verification = {field: request.headers.get(header) for field, header in header_names.items()}
    if not all(verification.values()):
        raise HTTPException(400, "Missing PayPal verification headers.")
    result = rest(
        paypal,
        "/v1/notifications/verify-webhook-signature",
        body={**verification, "webhook_id": webhook_id, "webhook_event": event},
    )
    if result.get("verification_status") != "SUCCESS":
        raise HTTPException(400, "PayPal could not verify this webhook.")
    if event.get("event_type") in {
        "CUSTOMER.DISPUTE.CREATED",
        "CUSTOMER.DISPUTE.UPDATED",
        "CUSTOMER.DISPUTE.RESOLVED",
    }:
        dispute_id = event.get("resource", {}).get("dispute_id")
        if isinstance(dispute_id, str):
            raw = dispute_detail(paypal, dispute_id)
            with db.begin():
                save_dispute(db, os.environ.get("POL_MERCHANT_ID", "kiln-and-ash"), raw)
    return {"accepted": True}
