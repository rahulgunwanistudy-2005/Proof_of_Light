# Implementation references checked 8 Nov 2026

Official documentation read through Firecrawl before the corresponding API code:

| Source | Used for |
| --- | --- |
| https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia | Secure context, explicit camera permission, audio false, preferred front camera and ideal constraints |
| https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback | Callback scheduling and presentationTime / captureTime clock distinction; rAF fallback limitations |
| https://numpy.org/doc/stable/reference/generated/numpy.savez_compressed.html | Numeric array NPZ export and avoiding pickle/object data |
| https://fastapi.tiangolo.com/tutorial/body/ | BaseModel request body validation; old request-body URL returned 404, official search located the current path |
| https://fastapi.tiangolo.com/tutorial/body-fields/ | Field limits on input lists |
| https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html | Distinguishing opposing flash transitions from color changes; rate constraints and warning against a safety certification claim |

The supplied business/hackathon research is preserved separately and has not
been independently rechecked. No PayPal, Gemini, Render or sponsor API is coded
in Phase 0, so those current contracts have not yet been researched.

## Capture-assistance foundation
- SQLAlchemy 2.0 typed declarative mappings and transactions:
  https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- Alembic environment, revisions, upgrade/check/downgrade:
  https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Official APIMatic PayPal context package, installation and Python skills:
  https://github.com/paypaldev/server-sdk-context-plugin-preview
- SDK source corresponding to the installed 2.4.0 package was read in place:
  `paypalserversdk/configuration.py`, `paypal_serversdk_client.py`,
  `controllers/orders_controller.py`, `http/auth/o_auth_2.py`, request/money/item
  models and `exceptions/api_exception.py`. Package source is not vendored.
- PayPal Orders reference: https://developer.paypal.com/docs/api/orders/v2/
  The website exposed endpoint paths but not complete field details through
  retrieval; exact checkout signatures and serialization were confirmed in SDK
  source and exercised through its transport seam.
- Official Disputes OpenAPI specification retrieved and relevant GET operation
  parameters read, before further dispute code (not implemented yet):
  https://github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/customer_disputes_v1.json
- Render MCP capability and workspace-selection reference:
  https://render.com/docs/mcp-server.md
