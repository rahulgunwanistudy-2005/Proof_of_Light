import pytest
import requests
from fastapi import HTTPException
from test_review import review  # noqa: F401 - pytest fixture

from apps.api.review.assessment import analyze


@pytest.mark.parametrize(
    ("provider_status", "message"),
    [(402, "billing or quota"), (429, "request limit")],
)
def test_unavailable_gemini_quota_reports_recoverable_error(monkeypatch, provider_status, message):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    response = requests.Response()
    response.status_code = provider_status
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(HTTPException, match=message) as error:
        analyze(b"test-image", "Test statement")
    assert error.value.status_code == 503


def test_consented_ai_notes_are_saved_once_and_shown_to_the_merchant(review, monkeypatch):  # noqa: F811
    import base64
    import io

    from PIL import Image

    from apps.api.review import assessment as module

    client, _ = review
    calls = []

    def fake_analyze(image, statement):
        calls.append((image[:2], statement))
        return {
            "visible_condition": "A chip is visible on the rim.",
            "uncertainty": "The back of the rim is not shown.",
            "follow_up": "Photograph the rim from above.",
            "model": "gemini-test",
        }

    monkeypatch.setattr(module, "analyze", fake_analyze)
    snapshot = {
        "paypal_order_id": "ai-test-order",
        "capture_id": "ai-test-capture",
        "amount_minor": 4800,
        "currency": "USD",
    }
    case = client.post("/api/review/cases", json=snapshot).json()["id"]
    endpoint = f"/api/review/cases/{case}/assessment"
    assert client.post(endpoint).status_code == 422  # no evidence yet

    invite = client.post(f"/api/review/cases/{case}/invitations").json()["path"].split("#")[1]
    photo = io.BytesIO()
    Image.new("RGB", (32, 32), "#cc8855").save(photo, "PNG")
    submission = {
        "statement": "There is a chip on the rim.",
        "photo": base64.b64encode(photo.getvalue()).decode(),
        "ai_consent": True,
    }
    sent = client.post("/api/claim/evidence", headers={"X-Claim-Token": invite}, json=submission)
    assert sent.status_code == 201, sent.text

    first = client.post(endpoint)
    assert first.status_code == 200, first.text
    assert first.json()["model"] == "gemini-test"
    assert client.post(endpoint).json() == first.json()
    assert len(calls) == 1 and calls[0] == (b"\xff\xd8", "There is a chip on the rim.")

    evidence = client.get(f"/api/review/cases/{case}/evidence").json()
    assert evidence["assessment"]["visible_condition"] == "A chip is visible on the rim."
    history = client.get(f"/api/review/cases/{case}").json()
    assert "ai_notes_added" in str(history)
