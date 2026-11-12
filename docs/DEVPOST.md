# Proof of Light submission draft

Proof of Light gives buyers a guided way to document item condition and merchants a case file for refund review. The buyer follows an invitation, describes the issue and attaches a photo or captures the item with a light sequence. The merchant can compare the evidence, download a PDF and review an exact refund before sending it to PayPal sandbox.

The light sequence provides a diagnostic signal. During development, an adaptive synthetic upload produced a matching result without a physical camera. We kept the measurement advisory and designed alternate submission paths for buyers who skip or cannot complete the sequence. Gemini can add structured notes about visible condition and uncertainty when the buyer opts in. The merchant authorizes financial actions.

Built with FastAPI, SQLAlchemy, Alembic, PostgreSQL, the PayPal Server SDK and APIMatic context, PayPal sandbox APIs, Gemini structured output, and a Render Blueprint. The local practice flow and stubbed provider tests passed. Add live provider results, hosted URL and the recorded video to the submission after verification. Sponsor eligibility and deployment status still need confirmation.

## Judge testing instructions

Open `/practice` on the demo site and start a practice case. Open the buyer form, submit a sample statement with optional item evidence, and return to the practice case. Select **Refresh cases**, download the evidence PDF, and prepare a practice refund. Check the amount and destination and approve it. The demo uses a fictional order and saves the approval in Proof of Light.
