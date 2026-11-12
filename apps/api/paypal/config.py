import os
from functools import lru_cache

from fastapi import HTTPException, Request

from .checkout import SandboxCheckout


def configured() -> bool:
    return bool(
        os.environ.get("PAYPAL_CLIENT_ID")
        and os.environ.get("PAYPAL_CLIENT_SECRET")
        and os.environ.get("PAYPAL_ENVIRONMENT", "sandbox") == "sandbox"
    )


@lru_cache(maxsize=1)
def client(client_id: str, secret: str):
    return SandboxCheckout(client_id, secret)


def sandbox():
    if not configured():
        raise HTTPException(503, "PayPal sandbox credentials are required for this action.")
    return client(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"])


def public_origin(request: Request) -> str:
    render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if render_host and request.url.hostname == render_host:
        return f"https://{render_host}"
    return str(request.base_url).rstrip("/")
