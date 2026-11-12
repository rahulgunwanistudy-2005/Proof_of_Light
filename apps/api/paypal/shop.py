"""Public sandbox checkout, with durable correlation and server-owned prices."""

import os
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.api.review import service
from apps.api.review.models import CheckoutOrder
from apps.api.review.router import DB, Merchant
from apps.api.review.schemas import CaseSnapshot, StrictModel

from .checkout import CATALOG, PayPalFailure, SandboxCheckout
from .config import configured, public_origin, sandbox

router = APIRouter(tags=["sandbox shop"])
Client = Annotated[SandboxCheckout, Depends(sandbox)]


class OrderStart(StrictModel):
    sku: str = Field(max_length=32)
    checkout_id: str = Field(pattern=r"^[a-f0-9]{32}$")


@router.get("/api/shop")
def catalog():
    return {
        "sandbox_ready": configured(),
        "products": [dict(item, sku=sku) for sku, item in CATALOG.items()],
    }


def order_json(row):
    return {
        "checkout_id": row.id,
        "sku": row.sku,
        "amount_minor": row.amount_minor,
        "currency": row.currency,
        "status": row.status,
        "paypal_order_id": row.paypal_id,
        "capture_id": row.capture_id,
        "approval_url": row.approval_url,
        "tracking": row.tracking,
    }


@router.post("/api/shop/orders")
def create_order(body: OrderStart, request: Request, db: DB, paypal: Client):
    product = CATALOG.get(body.sku)
    if product is None:
        raise HTTPException(404, "Product not found.")
    # Commit the stable operation identity before the provider request. Repeating
    # the same browser operation can safely recover the provider response.
    try:
        with db.begin():
            if db.get(CheckoutOrder, body.checkout_id) is None:
                db.add(
                    CheckoutOrder(
                        id=body.checkout_id,
                        merchant_id=os.environ.get("POL_MERCHANT_ID", "kiln-and-ash"),
                        sku=body.sku,
                        amount_minor=product["amount_minor"],
                        currency=product["currency"],
                    )
                )
    except IntegrityError:
        # Concurrent retries converge on the same operation row.
        pass
    with db.begin():
        row = db.scalar(
            select(CheckoutOrder).where(CheckoutOrder.id == body.checkout_id).with_for_update()
        )
        if row is None or row.sku != body.sku or time.time() - row.created_at > 3600:
            raise HTTPException(409, "Start a new checkout for this item.")
        if row.paypal_id is None:
            base = public_origin(request)
            response = paypal.create_order(
                row.sku,
                row.id,
                return_url=f"{base}/shop?checkout={row.id}",
                cancel_url=f"{base}/shop?cancelled=1",
            )
            order_id = response.data.get("id", "")
            url = next(
                (
                    link.get("href", "")
                    for link in response.data.get("links", [])
                    if link.get("rel") in {"approve", "payer-action"}
                ),
                "",
            )
            parsed = urlsplit(url)
            if (
                not re.fullmatch(r"[A-Z0-9]{10,32}", order_id)
                or parsed.scheme != "https"
                or parsed.netloc != "www.sandbox.paypal.com"
            ):
                raise HTTPException(502, "PayPal did not return a sandbox approval link.")
            row.paypal_id, row.approval_url, row.status = order_id, url, "AWAITING_BUYER"
        return order_json(row)


def match_capture(data, row):
    if data.get("id") != row.paypal_id or data.get("status") != "COMPLETED":
        return None
    for unit in data.get("purchase_units", []):
        if unit.get("custom_id") != row.id:
            continue
        for capture in unit.get("payments", {}).get("captures", []):
            amount = capture.get("amount", {})
            try:
                minor = Decimal(amount.get("value", "0")) * 100
            except InvalidOperation:
                continue
            capture_id = capture.get("id", "")
            if (
                capture.get("status") == "COMPLETED"
                and amount.get("currency_code") == row.currency
                and minor == row.amount_minor
                and re.fullmatch(r"[A-Z0-9]{10,32}", capture_id)
            ):
                return capture_id
    return None


@router.post("/api/shop/orders/{checkout_id}/capture")
def capture(checkout_id: str, db: DB, paypal: Client):
    with db.begin():
        row = db.scalar(
            select(CheckoutOrder).where(CheckoutOrder.id == checkout_id).with_for_update()
        )
        if row is None or not row.paypal_id or time.time() - row.created_at > 3600:
            raise HTTPException(404, "Checkout expired. Start a new checkout.")
        if row.status == "COMPLETED":
            return order_json(row)
        current = paypal.get_order(row.paypal_id).data
        if current.get("status") == "APPROVED":
            result = paypal.capture_order(row.paypal_id, row.id).data
            # The order read includes the stored custom_id even when the capture
            # response omits it.
            current = result if match_capture(result, row) else paypal.get_order(row.paypal_id).data
        if capture_id := match_capture(current, row):
            row.capture_id, row.status = capture_id, "COMPLETED"
        elif current.get("status") == "COMPLETED":
            row.status = "RECONCILE"
        else:
            row.status = "AWAITING_BUYER"
        return order_json(row)


@router.get("/api/review/shop-orders")
def orders(db: DB, actor: Merchant):
    return [
        order_json(row)
        for row in db.scalars(
            select(CheckoutOrder)
            .where(CheckoutOrder.merchant_id == actor, CheckoutOrder.status == "COMPLETED")
            .limit(100)
        )
    ]


@router.post("/api/review/shop-orders/{checkout_id}/case", status_code=201)
def make_case(checkout_id: str, db: DB, actor: Merchant):
    with db.begin():
        row = db.get(CheckoutOrder, checkout_id)
        if row is None or row.merchant_id != actor or row.status != "COMPLETED":
            raise HTTPException(404, "Completed sandbox order not found.")
        case = service.create_case(
            db,
            actor,
            CaseSnapshot(
                paypal_order_id=row.paypal_id,
                capture_id=row.capture_id,
                amount_minor=row.amount_minor,
                currency=row.currency,
                shipment=row.tracking or {},
            ),
        )
        return {"id": case.id}


def provider_error(error: PayPalFailure):
    detail = "PayPal sandbox could not complete the request."
    if error.kind.startswith("outcome_unknown"):
        detail = "PayPal's response was interrupted. Check the provider status before retrying."
    if error.debug_id:
        detail += f" PayPal reference {error.debug_id}."
    return HTTPException(502, detail)


class Tracking(StrictModel):
    carrier: str = Field(pattern=r"^[A-Z0-9_]{2,40}$")
    tracking_number: str = Field(pattern=r"^[A-Za-z0-9-]{3,120}$")


@router.post("/api/review/shop-orders/{checkout_id}/tracking")
def track(checkout_id: str, body: Tracking, db: DB, actor: Merchant, paypal: Client):
    with db.begin():
        row = db.scalar(
            select(CheckoutOrder).where(CheckoutOrder.id == checkout_id).with_for_update()
        )
        if row is None or row.merchant_id != actor or row.status != "COMPLETED":
            raise HTTPException(404, "Completed sandbox order not found.")
        if row.tracking:
            raise HTTPException(
                409, "This order already has a tracking record. Manage it in PayPal."
            )
        result = paypal.add_tracking(
            row.paypal_id, row.capture_id, body.carrier, body.tracking_number
        )
        row.tracking = {**body.model_dump(), "paypal_debug_id": result.debug_id}
        return order_json(row)
