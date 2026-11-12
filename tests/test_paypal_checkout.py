"""SDK transport contract tests. Stubbed PayPal responses, no real transactions."""

import json

import pytest
import requests
from requests.adapters import BaseAdapter

from apps.api.paypal.checkout import PayPalFailure, SandboxCheckout, request_id


class SandboxStub(BaseAdapter):
    def __init__(self, statuses=None, disconnect=False):
        self.requests = []
        self.statuses = list(statuses or [201])
        self.disconnect = disconnect

    def send(self, request, **kwargs):
        assert request.url.startswith("https://api-m.sandbox.paypal.com/")
        self.requests.append(request)
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.headers["content-type"] = "application/json"
        response.headers["PayPal-Debug-Id"] = "stub-debug-id"
        if request.url.endswith("/v1/oauth2/token"):
            response.status_code = 200
            response._content = json.dumps(
                {"access_token": "stub-token", "token_type": "Bearer", "expires_in": 3600}
            ).encode()
        else:
            if self.disconnect:
                raise requests.ConnectionError("Stub transport disconnected")
            response.status_code = self.statuses.pop(0) if self.statuses else 201
            response._content = json.dumps(
                {"id": "9AB1234567890", "status": "CREATED"}
                if response.status_code < 400
                else {"name": "STUB_ERROR", "message": "Test failure"}
            ).encode()
        return response

    def close(self):
        pass


def client(statuses=None, disconnect=False):
    adapter = SandboxStub(statuses, disconnect)
    session = requests.Session()
    session.mount("https://", adapter)
    return SandboxCheckout(
        "stub-client", "stub-secret", http_session=session, sleep=lambda _: None
    ), adapter


def test_actual_sdk_serializes_catalog_and_preserves_request_id():
    paypal, stub = client()
    result = paypal.create_order("KA-MUG-01", "local-operation-123")
    assert result.status_code == 201
    assert result.debug_id == "stub-debug-id"
    request = stub.requests[-1]
    assert request.method == "POST"
    assert request.url.endswith("/v2/checkout/orders")
    assert request.headers["PayPal-Request-Id"] == result.request_id
    assert request.headers["Prefer"] == "return=representation"
    payload = json.loads(request.body)
    unit = payload["purchase_units"][0]
    assert payload["intent"] == "CAPTURE"
    assert unit["amount"]["value"] == "48.00"
    assert unit["amount"]["breakdown"]["item_total"]["value"] == "48.00"
    assert unit["items"][0]["sku"] == "KA-MUG-01"


def test_retries_transient_responses_with_one_stable_key():
    paypal, stub = client([503, 429, 201])
    assert paypal.create_order("KA-MUG-01", "retry-operation-123").status_code == 201
    orders = [r for r in stub.requests if "/checkout/orders" in r.url]
    assert len(orders) == 3
    assert len({r.headers["PayPal-Request-Id"] for r in orders}) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_no_retry_of_business_or_authentication_rejection(status):
    paypal, stub = client([status, 201])
    with pytest.raises(PayPalFailure) as error:
        paypal.create_order("KA-MUG-01", "failed-operation-123")
    assert error.value.status == status
    assert error.value.debug_id == "stub-debug-id"
    assert len([r for r in stub.requests if "/checkout/orders" in r.url]) == 1


def test_transport_failure_is_unknown_not_falsely_failed():
    paypal, stub = client(disconnect=True)
    with pytest.raises(PayPalFailure, match="outcome_unknown"):
        paypal.capture_order("9AB1234567890", "capture-operation-123")
    assert len([r for r in stub.requests if "/checkout/orders" in r.url]) == 1


def test_cached_oauth_token_and_capture_wire_path():
    paypal, stub = client()
    paypal.create_order("KA-MUG-01", "create-operation-123")
    paypal.capture_order("9AB1234567890", "capture-operation-123")
    assert len([r for r in stub.requests if r.url.endswith("/v1/oauth2/token")]) == 1
    assert stub.requests[-1].url.endswith("/v2/checkout/orders/9AB1234567890/capture")
    assert stub.requests[-1].headers["PayPal-Request-Id"] == request_id(
        "capture_order", "capture-operation-123"
    )


def test_production_environment_is_rejected():
    with pytest.raises(ValueError, match="sandbox only"):
        SandboxCheckout("client", "secret", environment="production")


def test_refund_wire_amount_and_merchant_request_id():
    paypal, stub = client()
    key = "b" * 32
    paypal.refund("9AB1234567890", 1205, "USD", key)
    request = stub.requests[-1]
    assert request.url.endswith("/v2/payments/captures/9AB1234567890/refund")
    assert request.headers["PayPal-Request-Id"] == key
    assert json.loads(request.body)["amount"] == {"currency_code": "USD", "value": "12.05"}


def test_checkout_return_url_is_serialized_in_paypal_experience_context():
    paypal, stub = client()
    paypal.create_order(
        "KA-MUG-01",
        "local-operation-123",
        return_url="https://example.com/shop",
        cancel_url="https://example.com/shop?cancelled=1",
    )
    source = json.loads(stub.requests[-1].body)["payment_source"]["paypal"]["experience_context"]
    assert source["return_url"] == "https://example.com/shop"
    assert source["cancel_url"] == "https://example.com/shop?cancelled=1"
