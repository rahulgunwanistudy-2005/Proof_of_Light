import base64
import io

from PIL import Image
from test_review import review  # noqa: F401 - pytest fixture

from apps.api.main import app
from apps.api.paypal.checkout import PayPalResult
from apps.api.paypal.config import sandbox


class SandboxStub:
    order_id = "1ABC2345678901234"
    capture_id = "2ABC2345678901234"

    def __init__(self):
        self.calls = []
        self.status = "CREATED"

    def create_order(self, sku, operation_id, **urls):
        self.operation_id = operation_id
        assert urls["return_url"].endswith(operation_id)
        self.calls.append(("create", sku))
        return PayPalResult(
            {
                "id": self.order_id,
                "links": [
                    {
                        "rel": "payer-action",
                        "href": "https://www.sandbox.paypal.com/checkoutnow?token=" + self.order_id,
                    }
                ],
            },
            201,
            "create",
            operation_id,
        )

    def get_order(self, order_id):
        assert order_id == self.order_id
        return PayPalResult(
            {
                "id": self.order_id,
                "status": self.status,
                "purchase_units": [
                    {
                        "custom_id": self.operation_id,
                        "payments": {
                            "captures": [
                                {
                                    "id": self.capture_id,
                                    "status": "COMPLETED",
                                    "amount": {"value": "48.00", "currency_code": "USD"},
                                }
                            ]
                        },
                    }
                ],
            },
            200,
            "read",
            None,
        )

    def capture_order(self, order_id, operation_id):
        assert self.status == "APPROVED"
        self.calls.append(("capture", operation_id))
        self.status = "COMPLETED"
        return self.get_order(order_id)

    def refund(self, capture_id, amount, currency, request_id):
        assert (capture_id, amount, currency) == (self.capture_id, 1000, "USD")
        self.calls.append(("refund", request_id))
        return PayPalResult({"id": "REFUND-STUB", "status": "COMPLETED"}, 201, "refund", request_id)


def test_checkout_evidence_and_approved_refund_flow(review):  # noqa: F811 - pytest fixture
    client, _ = review
    paypal = SandboxStub()
    app.dependency_overrides[sandbox] = lambda: paypal
    operation = "a" * 32
    start = {"checkout_id": operation, "sku": "KA-MUG-01"}
    first = client.post("/api/shop/orders", json=start)
    assert first.status_code == 200, first.text
    assert client.post("/api/shop/orders", json=start).json() == first.json()
    assert client.post(f"/api/shop/orders/{operation}/capture").json()["status"] == "AWAITING_BUYER"
    paypal.status = "APPROVED"
    assert client.post(f"/api/shop/orders/{operation}/capture").json()["status"] == "COMPLETED"
    case = client.post(f"/api/review/shop-orders/{operation}/case").json()["id"]
    invite = client.post(f"/api/review/cases/{case}/invitations").json()["path"].split("#")[1]
    photo = io.BytesIO()
    Image.new("RGB", (32, 32), "#cc8855").save(photo, "PNG")
    submission = {
        "statement": "There is a chip on the rim.",
        "photo": base64.b64encode(photo.getvalue()).decode(),
    }
    headers = {"X-Claim-Token": invite}
    assert client.post("/api/claim/evidence", headers=headers, json=submission).status_code == 201
    assert client.post("/api/claim/evidence", headers=headers, json=submission).status_code == 409
    evidence = client.get(f"/api/review/cases/{case}/evidence").json()
    assert evidence["statement"] == submission["statement"] and evidence["has_image"]
    assert client.get(f"/api/review/cases/{case}/packet.pdf").content.startswith(b"%PDF-")
    proposal = client.post(
        f"/api/review/cases/{case}/proposals",
        json={
            "financial_action": {
                "action": "refund_capture",
                "amount_minor": 1000,
                "currency": "USD",
                "target_id": paypal.capture_id,
            },
            "explanation": "Partial refund for chipped rim",
        },
    ).json()
    approval = client.post(
        f"/api/review/proposals/{proposal['id']}/approve",
        json={
            "expected_payload_hash": proposal["payload_hash"],
            "expected_case_version": proposal["case_version"],
            "confirm": True,
        },
    ).json()
    assert [kind for kind, _ in paypal.calls] == ["create", "capture"]
    endpoint = f"/api/review/actions/{approval['outbox_id']}/send"
    result = client.post(endpoint)
    assert result.status_code == 200, result.text
    assert result.json()["paypal_executed"] is True
    assert client.post(endpoint).status_code == 409
    assert paypal.calls[-1] == ("refund", approval["request_id"])


def test_webhook_signature_gate_and_repeated_event(review, monkeypatch):  # noqa: F811
    from apps.api.paypal import disputes

    client, _ = review
    app.dependency_overrides[sandbox] = lambda: object()
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "stub-webhook-id")
    item = {
        "dispute_id": "PP-STUB-0001",
        "dispute_amount": {"currency_code": "USD", "value": "48.00"},
        "status": "WAITING_FOR_SELLER_RESPONSE",
        "dispute_life_cycle_stage": "INQUIRY",
    }
    verified = False

    def provider(paypal, path, *, body=None):
        if path == "/v1/notifications/verify-webhook-signature":
            assert body["webhook_id"] == "stub-webhook-id"
            return {"verification_status": "SUCCESS" if verified else "FAILURE"}
        assert path == "/v1/customer/disputes/PP-STUB-0001"
        return item

    monkeypatch.setattr(disputes, "rest", provider)
    headers = {
        f"paypal-{field}": "stub-header"
        for field in (
            "auth-algo",
            "cert-url",
            "transmission-id",
            "transmission-sig",
            "transmission-time",
        )
    }
    event = {
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "resource": {"dispute_id": item["dispute_id"]},
    }
    assert client.post("/api/paypal/webhooks", json=event, headers=headers).status_code == 400
    assert client.get("/api/review/cases").json() == []
    verified = True
    assert client.post("/api/paypal/webhooks", json=event, headers=headers).status_code == 200
    assert client.post("/api/paypal/webhooks", json=event, headers=headers).status_code == 200
    cases = client.get("/api/review/cases").json()
    assert len(cases) == 1
    assert cases[0]["snapshot"]["provider_dispute"]["id"] == item["dispute_id"]
