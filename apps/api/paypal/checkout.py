"""Real PayPal SDK serialization, sandbox only; not yet exposed as public checkout.

Grounding: APIMatic PayPal context plugin python-* skills, SDK 2.4.0 source
controllers/orders_controller.py, models/order_request.py, configuration.py.
REST reference: https://developer.paypal.com/docs/api/orders/v2/
"""

import hashlib
import json
import random
import re
import threading
import time
from dataclasses import dataclass

import requests
from apimatic_core.exceptions.auth_validation_exception import AuthValidationException
from paypalserversdk.configuration import Environment, Server
from paypalserversdk.exceptions.api_exception import ApiException
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

CATALOG = {
    "KA-MUG-01": {"name": "Everyday mug", "amount_minor": 4800, "currency": "USD"},
    "KA-BOWL-01": {"name": "Breakfast bowl", "amount_minor": 5600, "currency": "USD"},
    "KA-PLATE-01": {"name": "Side plate", "amount_minor": 3800, "currency": "USD"},
}


def request_id(operation: str, operation_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", operation_id):
        raise ValueError("Use a stable, server-recorded operation ID")
    return hashlib.sha256(f"pol:{operation}:{operation_id}".encode()).hexdigest()[:32]


@dataclass(frozen=True)
class PayPalResult:
    data: dict
    status_code: int
    debug_id: str | None
    request_id: str | None


class PayPalFailure(Exception):
    def __init__(self, kind: str, status: int | None = None, debug_id: str | None = None):
        super().__init__(kind)
        self.kind, self.status, self.debug_id = kind, status, debug_id


def debug_id(headers) -> str | None:
    return next(
        (str(value) for key, value in (headers or {}).items() if key.lower() == "paypal-debug-id"),
        None,
    )


class SandboxCheckout:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        environment="sandbox",
        http_session=None,
        sleep=time.sleep,
    ):
        if environment != "sandbox":
            raise ValueError("Proof of Light permits PayPal sandbox only")
        if not client_id or not client_secret:
            raise ValueError("Sandbox client ID and secret are required")
        self._sdk = PaypalServersdkClient(
            environment=Environment.SANDBOX,
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                o_auth_client_id=client_id, o_auth_client_secret=client_secret
            ),
            timeout=15,
            max_retries=0,
            http_client_instance=http_session,
        )
        if self._sdk.config.get_base_uri(Server.DEFAULT) != "https://api-m.sandbox.paypal.com":
            raise ValueError("SDK did not resolve to the sandbox host")
        self._lock = threading.RLock()
        self._sleep = sleep

    def _call(self, operation, options, key=None) -> PayPalResult:
        with self._lock:  # Protect the shared SDK's OAuth cache across worker threads.
            for attempt in range(3):
                try:
                    result = operation(options)
                    data = json.loads(result.text) if result.text else {}
                    return PayPalResult(data, result.status_code, debug_id(result.headers), key)
                except ApiException as exc:
                    status = exc.response_code
                    if (status == 429 or 500 <= status <= 599) and attempt < 2:
                        # Same idempotency key on every retry. The SDK retry layer
                        # stays off so nested retries cannot multiply requests.
                        self._sleep(0.25 * 2**attempt + random.uniform(0, 0.15))
                        continue
                    raise PayPalFailure(
                        "paypal_rejected_request", status, debug_id(exc.response.headers)
                    ) from None
                except AuthValidationException:
                    raise PayPalFailure("sandbox_authentication_failed") from None
                except requests.RequestException:
                    # A transport timeout may follow a completed write. Do not
                    # blindly reissue it with a fresh key or claim it failed.
                    raise PayPalFailure("outcome_unknown_reconcile_before_retry") from None
        raise RuntimeError("Unreachable retry state")

    def create_order(self, sku: str, operation_id: str) -> PayPalResult:
        product = CATALOG.get(sku)
        if product is None:
            raise ValueError("Product not found")
        minor = product["amount_minor"]
        money = {"currency_code": product["currency"], "value": f"{minor // 100}.{minor % 100:02d}"}
        body = OrderRequest.from_dictionary(
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "custom_id": operation_id,
                        "amount": {**money, "breakdown": {"item_total": money}},
                        "items": [
                            {
                                "name": product["name"],
                                "sku": sku,
                                "quantity": "1",
                                "unit_amount": money,
                            }
                        ],
                    }
                ],
            }
        )
        key = request_id("create_order", operation_id)
        return self._call(
            self._sdk.orders.create_order,
            {"body": body, "paypal_request_id": key, "prefer": "return=representation"},
            key,
        )

    def get_order(self, order_id: str) -> PayPalResult:
        self._order_id(order_id)
        return self._call(self._sdk.orders.get_order, {"id": order_id})

    def capture_order(self, order_id: str, operation_id: str) -> PayPalResult:
        self._order_id(order_id)
        key = request_id("capture_order", operation_id)
        return self._call(
            self._sdk.orders.capture_order,
            {"id": order_id, "paypal_request_id": key, "prefer": "return=representation"},
            key,
        )

    @staticmethod
    def _order_id(order_id):
        if not re.fullmatch(r"[A-Z0-9]{10,32}", order_id):
            raise ValueError("Invalid PayPal order ID")
