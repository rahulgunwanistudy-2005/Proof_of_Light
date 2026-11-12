import base64
import io
import time

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_review import review  # noqa: F401 - pytest fixture

from apps.api.main import STARTS, app
from apps.api.paypal.config import sandbox
from apps.api.review import assessment
from apps.api.review.models import Audit, Case, Evidence
from apps.api.review.practice_access import issue_practice


@pytest.fixture(autouse=True)
def clear_practice_limit(monkeypatch):
    monkeypatch.setitem(STARTS, "/api/practice", {})


def start(client):
    response = client.post("/api/practice")
    assert response.status_code == 201, response.text
    data = response.json()
    return data, {"X-Practice-Token": data["token"]}


def fake_notes(image, statement):
    return {
        "visible_condition": "A chip is visible on the rim.",
        "uncertainty": "Only one angle is shown.",
        "follow_up": "Photograph the rim from above.",
        "model": "gemini-test",
    }


def practice_case_with_photo(client):
    session, practice = start(client)
    claim = {"X-Claim-Token": session["claim_path"].split("#")[1]}
    picture = io.BytesIO()
    Image.new("RGB", (32, 32), "tan").save(picture, "PNG")
    evidence = {
        "statement": "The sample mug has a chipped rim.",
        "photo": base64.b64encode(picture.getvalue()).decode(),
        "ai_consent": True,
    }
    assert client.post("/api/claim/evidence", json=evidence, headers=claim).status_code == 201
    return f"/api/review/cases/{session['case_id']}", practice


def test_public_practice_uses_real_review_without_provider_access(review, monkeypatch):  # noqa: F811
    client, _ = review
    monkeypatch.setattr(assessment, "analyze", fake_notes)
    monkeypatch.setattr(assessment, "PRACTICE_CALLS", [])
    app.dependency_overrides[sandbox] = object
    client.headers.pop("Authorization")
    session, practice = start(client)
    case_path = f"/api/review/cases/{session['case_id']}"
    claim = {"X-Claim-Token": session["claim_path"].split("#")[1]}
    assert client.get("/api/claim", headers=claim).json() == {"submitted": False, "practice": True}

    picture = io.BytesIO()
    Image.new("RGB", (32, 32), "tan").save(picture, "PNG")
    evidence = {
        "statement": "The sample mug has a chipped rim.",
        "photo": base64.b64encode(picture.getvalue()).decode(),
        "ai_consent": True,
    }
    assert client.post("/api/claim/evidence", json=evidence, headers=claim).status_code == 201
    assert client.post("/api/claim/evidence", json=evidence, headers=claim).status_code == 409
    record = client.get(f"{case_path}/evidence", headers=practice).json()
    assert record["statement"] == evidence["statement"] and record["has_image"]
    assert record["ai_consent"] is True
    assert client.get(f"{case_path}/packet.pdf", headers=practice).content.startswith(b"%PDF-")
    notes = client.post(f"{case_path}/assessment", headers=practice)
    assert notes.status_code == 200, notes.text
    assert notes.json()["model"] == "gemini-test"
    assert client.get("/api/review/disputes", headers=practice).status_code == 401
    assert client.get("/api/review/shop-orders", headers=practice).status_code == 401
    assert client.post(f"{case_path}/invitations", headers=practice).status_code == 401

    record = client.get(case_path, headers=practice).json()
    proposal = client.post(
        f"{case_path}/proposals",
        headers=practice,
        json={
            "financial_action": {
                "action": "refund_capture",
                "amount_minor": 1000,
                "currency": "USD",
                "target_id": record["snapshot"]["capture_id"],
            },
            "explanation": "Practice refund.",
        },
    )
    assert proposal.status_code == 201, proposal.text
    proposal = proposal.json()
    approval_path = f"/api/review/proposals/{proposal['id']}/approve"
    body = {
        "expected_payload_hash": proposal["payload_hash"],
        "expected_case_version": proposal["case_version"],
        "confirm": False,
    }
    assert client.post(approval_path, headers=practice, json=body).status_code == 422
    approved = client.post(approval_path, headers=practice, json={**body, "confirm": True})
    assert approved.status_code == 200, approved.text
    assert approved.json()["paypal_executed"] is False
    send = f"/api/review/actions/{approved.json()['outbox_id']}/send"
    assert client.post(send, headers=practice).status_code == 401


def test_practice_sessions_are_isolated_and_expired_cases_are_removed(review):  # noqa: F811
    client, engine = review
    actual = client.post(
        "/api/review/cases",
        json={"paypal_order_id": "merchant-only", "amount_minor": 4800, "currency": "USD"},
    ).json()["id"]
    authorization = client.headers.pop("Authorization")
    first, first_headers = start(client)
    second, second_headers = start(client)
    first_case = f"/api/review/cases/{first['case_id']}"
    actual_case = f"/api/review/cases/{actual}"
    assert client.get(first_case).status_code == 401
    assert client.get(first_case, headers={"Authorization": authorization}).status_code == 404
    assert client.get(first_case, headers=second_headers).status_code == 404
    assert client.get(actual_case, headers=first_headers).status_code == 404
    assert [
        row["id"] for row in client.get("/api/review/cases", headers=second_headers).json()
    ] == [second["case_id"]]
    expired_token, _ = issue_practice(int(time.time()) - 1)
    assert client.get(first_case, headers={"X-Practice-Token": expired_token}).status_code == 401
    assert (
        client.get(first_case, headers={"X-Practice-Token": first["token"] + "x"}).status_code
        == 401
    )

    claim = {"X-Claim-Token": first["claim_path"].split("#")[1]}
    assert (
        client.post("/api/claim/evidence", headers=claim, json={"statement": "Sample."}).status_code
        == 201
    )
    with Session(engine) as db, db.begin():
        db.get(Case, first["case_id"]).created_at = 0
        db.get(Case, actual).created_at = 0
    start(client)
    assert client.get("/api/claim", headers=claim).status_code == 404
    assert client.get(first_case, headers=first_headers).status_code == 404
    assert client.get(actual_case, headers={"Authorization": authorization}).status_code == 200
    with Session(engine) as db:
        assert not db.scalars(select(Audit).where(Audit.case_id == first["case_id"])).all()
        assert not db.scalars(select(Evidence).where(Evidence.case_id == first["case_id"])).all()


def test_practice_ai_notes_share_an_hourly_budget(review, monkeypatch):  # noqa: F811
    client, _ = review
    client.headers.pop("Authorization")
    calls = []
    monkeypatch.setattr(
        assessment, "analyze", lambda *args: calls.append(args) or fake_notes(*args)
    )
    monkeypatch.setattr(assessment, "PRACTICE_CALLS", [])
    monkeypatch.setenv("POL_PRACTICE_AI_PER_HOUR", "1")
    first, first_token = practice_case_with_photo(client)
    second, second_token = practice_case_with_photo(client)
    assert client.post(f"{first}/assessment", headers=first_token).status_code == 200
    # Stored notes are returned again without spending budget.
    assert client.post(f"{first}/assessment", headers=first_token).status_code == 200
    limited = client.post(f"{second}/assessment", headers=second_token)
    assert limited.status_code == 429 and "limit" in limited.json()["detail"]
    assert len(calls) == 1
    # A practice token cannot request notes for another practice case.
    assert client.post(f"{second}/assessment", headers=first_token).status_code == 404
