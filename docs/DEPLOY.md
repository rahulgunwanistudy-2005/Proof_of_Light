# Sandbox and Render setup

## Verify the external integrations

1. Enter `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from a PayPal sandbox app in the ignored `.env`. Restart the local service after changes.
2. Run `.venv/bin/python -m scripts.check_sandbox` to verify OAuth. It performs a token exchange only.
3. Open `/shop`, approve an order with a sandbox buyer, return and select **Capture approved payment**. The merchant can find that order under **Completed sandbox orders**.
4. Open a case and invite the buyer. After reviewing evidence, prepare and approve the exact refund, then select **Send approved sandbox refund**. Confirm the status and refund ID in PayPal.
5. Use a sandbox buyer to open a dispute on a separate test order. Import it from **PayPal disputes**. For automatic intake, register `/api/paypal/webhooks` in the sandbox app and enter `PAYPAL_WEBHOOK_ID`. Subscribe to the created, updated and resolved dispute events. Webhook postback verification uses actual sandbox events.
6. Add `GEMINI_API_KEY` for image notes. A buyer must opt in and a merchant must select **Generate Gemini notes**. The `GEMINI_MODEL` default comes from the official structured-output reference.

Keep merchant credentials separate from buyer invitations and public testing instructions. The case packet can be downloaded for review or used in PayPal’s Resolution Center. One direct refund attempt is reserved per capture. Check pending or interrupted sends in PayPal using the displayed references.

## Deploy on Render

`render.yaml` defines one Python web service and one PostgreSQL database. The Blueprint uses paid compute plans. Review the cost and choose the intended workspace before applying it. The web service performs migrations before starting and serves the interface and API on one origin. One web process holds the short-lived camera challenges. Submitted evidence and approvals use PostgreSQL.

Publish the authorized source checkpoint to the linked GitHub repository, then create a Blueprint from that repository in the selected Render workspace. Fill provider secrets in the Dashboard. Render generates the merchant credential. Use the HTTPS service URL for buyer links and the webhook, and check `/health` plus the buyer and merchant pages after deployment.

The current Blueprint passed Render’s public JSON schema check. Local PostgreSQL migrations and the practice browser flow passed. Live Render provisioning, live provider tests and public judge access remain pending. See the [Render Blueprint spec](https://render.com/docs/blueprint-spec) and [PayPal webhook guide](https://developer.paypal.com/api/rest/webhooks/rest/).
