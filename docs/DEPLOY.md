# Sandbox and Render setup

## Verify the external integrations

1. In **Apps & Credentials** on the PayPal Developer Dashboard, choose **Sandbox** and create or open an app. Enter its client ID and secret as `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in the ignored `.env`. Restart the local service after changes. [PayPal sandbox setup](https://developer.paypal.com/api/get-started/)
2. Run `.venv/bin/python -m scripts.check_sandbox` to verify OAuth. It performs a token exchange only.
3. Open `/shop`, approve an order with a sandbox buyer, return and select **Capture approved payment**. The merchant can find that order under **Completed sandbox orders**.
4. Open a case and invite the buyer. After reviewing evidence, prepare and approve the exact refund, then select **Send approved sandbox refund**. Confirm the status and refund ID in PayPal.
5. Use a sandbox buyer to open a dispute on a separate test order. Import it from **PayPal disputes**. For automatic intake, register `/api/paypal/webhooks` in the sandbox app and enter `PAYPAL_WEBHOOK_ID`. Subscribe to the created, updated and resolved dispute events. Webhook postback verification uses actual sandbox events.
6. Create an authorization key in Google AI Studio and add it as `GEMINI_API_KEY`. In an authenticated merchant case, submit an image with the buyer's opt-in and select **Generate Gemini notes**. [Gemini API keys](https://aistudio.google.com/docs/api-key)

Keep merchant credentials separate from buyer invitations and public testing instructions. The case packet can be downloaded for review or used in PayPal’s Resolution Center. One direct refund attempt is reserved per capture. Check pending or interrupted sends in PayPal using the displayed references.

## Deploy on Render

`render.yaml` defines one Python web service and one PostgreSQL database. The Blueprint uses paid compute plans. Review the cost and choose the intended workspace before applying it. The web service performs migrations before starting and serves the interface and API on one origin. One web process holds the short-lived camera challenges. Submitted evidence and approvals use PostgreSQL.

1. Publish the reviewed local `main` branch to the linked GitHub repository with `git push -u origin main`.
2. In the intended Render workspace, choose **New → Blueprint**, connect that repository and branch, review the paid web and database plans, and deploy. Render generates `POL_MERCHANT_TOKEN` for the merchant console. [Create a Render Blueprint](https://render.com/docs/infrastructure-as-code#setup)
3. Open the assigned HTTPS URL and check `/health`. In a private window, open `/practice`, send a sample statement as the buyer, then refresh the review page and approve a practice refund. The judge path uses a fictional payment and needs no keys.
4. In the Render web service's **Environment** panel, enter `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `GEMINI_API_KEY` to enable the external integrations. Keep these values in Render and the ignored local `.env`. [Render environment variables](https://render.com/docs/configure-environment-variables)
5. Register `https://<service-host>/api/paypal/webhooks` in the PayPal sandbox app and add the resulting `PAYPAL_WEBHOOK_ID` in Render. Run the provider checks above on the hosted site using sandbox accounts. [PayPal webhooks](https://developer.paypal.com/api/rest/webhooks/rest/)

The app uses one web process for short-lived practice sessions and camera challenges. Practice invitations and review access expire after one hour. Starting another practice case clears expired practice records. Use the HTTPS `/practice` URL in judge instructions and keep the merchant credential in the dashboard.

For a temporary preview, choose `render.preview.yaml` as the Blueprint path. It uses a free web service and a free PostgreSQL database. The web service can spin down when idle, and the database expires 30 days after creation. Upgrade the database before it expires if the demo needs to stay available longer. [Render free-tier limits](https://render.com/docs/free)
