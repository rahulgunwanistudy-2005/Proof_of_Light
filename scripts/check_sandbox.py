"""Read-only PayPal sandbox credential check. No order, refund or dispute action."""

import os

from dotenv import load_dotenv
from paypalserversdk.exceptions.api_exception import ApiException
from requests import RequestException

from apps.api.paypal.checkout import SandboxCheckout


def main():
    load_dotenv()
    client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to the ignored .env file.")
        return 2
    checkout = SandboxCheckout(
        client_id, client_secret, environment=os.environ.get("PAYPAL_ENVIRONMENT", "sandbox")
    )
    try:
        token = checkout._sdk.auth_managers["Oauth2"].fetch_token()
    except ApiException as error:
        print(
            f"Sandbox token request failed with HTTP {error.response_code}. Credentials were not printed."
        )
        return 1
    except RequestException:
        print("Could not reach PayPal sandbox. No financial action was attempted.")
        return 1
    if not getattr(token, "access_token", None):
        print("Sandbox did not return an access token. No financial action was attempted.")
        return 1
    print(
        "PayPal sandbox token exchange succeeded. No order, refund or dispute action was attempted."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
