import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from apps.api.main import app
from apps.api.review import service
from apps.api.review.database import session
from apps.api.review.models import Approval, Audit, Base, Outbox, Proposal


@pytest.fixture
def review(tmp_path, monkeypatch):
    monkeypatch.setenv("POL_MERCHANT_TOKEN", "test-merchant-credential-" + "x" * 32)
    monkeypatch.setenv("POL_MERCHANT_ID", "kiln-and-ash")
    engine = create_engine(
        f"sqlite:///{tmp_path / 'review.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    def sessions():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[session] = sessions
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + "test-merchant-credential-" + "x" * 32
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def prepared(client, light="VERIFIED"):
    snapshot = {
        "paypal_order_id": "manual-test-order",
        "capture_id": "manual-test-capture",
        "dispute_id": "manual-test-dispute",
        "amount_minor": 4800,
        "currency": "USD",
        "light_response": light,
    }
    case_response = client.post("/api/review/cases", json=snapshot)
    assert case_response.status_code == 201, case_response.text
    case = case_response.json()
    body = {
        "financial_action": {
            "action": "refund_capture",
            "amount_minor": 1200,
            "currency": "USD",
            "target_id": "manual-test-capture",
        },
        "explanation": "Merchant suggested partial refund; manual test case.",
    }
    response = client.post(f"/api/review/cases/{case['id']}/proposals", json=body)
    assert response.status_code == 201, response.text
    proposal = response.json()
    approval = {
        "expected_payload_hash": proposal["payload_hash"],
        "expected_case_version": case["version"],
        "confirm": True,
    }
    return case, proposal, approval, body


@pytest.mark.parametrize(
    "light", ["VERIFIED", "FAILED", "INCONCLUSIVE", "DECLINED", "NOT_RECORDED"]
)
def test_every_signal_stays_pending_without_merchant_approval(review, light):
    client, engine = review
    _, proposal, _, _ = prepared(client, light)
    assert proposal["status"] == "PENDING_REVIEW"
    assert proposal["requires_approval"] is True
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Approval)) == 0
        assert db.scalar(select(func.count()).select_from(Outbox)) == 0


def test_explicit_review_queues_exactly_once_and_does_not_execute(review):
    client, engine = review
    case, proposal, approval, _ = prepared(client)
    url = f"/api/review/proposals/{proposal['id']}/approve"
    first = client.post(url, json=approval)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "AWAITING_EXECUTOR"
    assert first.json()["paypal_executed"] is False
    assert client.post(url, json=approval).json() == first.json()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Approval)) == 1
        assert db.scalar(select(func.count()).select_from(Outbox)) == 1
        action = service.ready_action(db, first.json()["outbox_id"])
        assert action["payload"]["amount_minor"] == 1200
        assert action["merchant_id"] == "kiln-and-ash"
        previous = "0" * 64
        for row in db.scalars(
            select(Audit).where(Audit.case_id == case["id"]).order_by(Audit.sequence)
        ):
            assert row.previous_hash == previous
            assert row.entry_hash == service.digest({"previous_hash": previous, "event": row.event})
            previous = row.entry_hash


def test_no_default_merchant_access(review, monkeypatch):
    client, _ = review
    monkeypatch.delenv("POL_MERCHANT_TOKEN")
    assert client.get("/api/review/cases").status_code == 503


def test_anonymous_and_wrong_token_cannot_review(review):
    client, _ = review
    _, proposal, approval, _ = prepared(client)
    client.headers.pop("Authorization")
    assert client.get("/api/review/cases").status_code == 401
    url = f"/api/review/proposals/{proposal['id']}/approve"
    assert client.post(url, json=approval).status_code == 401
    client.headers["Authorization"] = "Bearer wrong"
    assert client.post(url, json=approval).status_code == 401


def test_other_merchant_cannot_read_or_approve_case(review, monkeypatch):
    client, _ = review
    case, proposal, approval, _ = prepared(client)
    monkeypatch.setenv("POL_MERCHANT_ID", "another-merchant")
    assert client.get(f"/api/review/cases/{case['id']}").status_code == 404
    assert client.get("/api/review/cases").json() == []
    assert (
        client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).status_code
        == 404
    )


@pytest.mark.parametrize("confirm", [False, "true", 1, None])
def test_explicit_boolean_confirmation_required(review, confirm):
    client, _ = review
    _, proposal, approval, _ = prepared(client)
    approval["confirm"] = confirm
    assert (
        client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).status_code
        == 422
    )


def test_stale_case_invalidates_saved_approval(review):
    client, engine = review
    case, proposal, approval, _ = prepared(client)
    accepted = client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).json()
    snapshot = case["snapshot"] | {"claim_text": "New evidence changed the case"}
    response = client.put(
        f"/api/review/cases/{case['id']}", json={"expected_version": 1, "snapshot": snapshot}
    )
    assert response.json()["version"] == 2
    with Session(engine) as db, pytest.raises(service.ReviewError):
        service.ready_action(db, accepted["outbox_id"])
    assert (
        client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).status_code
        == 409
    )


def test_modified_financial_payload_is_blocked_at_execution_boundary(review):
    client, engine = review
    _, proposal, approval, _ = prepared(client)
    result = client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).json()
    with Session(engine) as db, db.begin():
        row = db.get(Outbox, result["outbox_id"])
        row.payload = row.payload | {"amount_minor": 4800}
    with Session(engine) as db, pytest.raises(service.ReviewError, match="match"):
        service.ready_action(db, result["outbox_id"])


@pytest.mark.parametrize(
    "change",
    [
        {"amount_minor": 4801},
        {"amount_minor": -1},
        {"currency": "EUR"},
        {"target_id": "another-capture"},
    ],
)
def test_proposal_cannot_exceed_purchase_or_change_destination(review, change):
    client, _ = review
    case, _, _, body = prepared(client)
    body["financial_action"].update(change)
    assert client.post(f"/api/review/cases/{case['id']}/proposals", json=body).status_code == 422


def test_rejected_proposal_cannot_be_approved(review):
    client, _ = review
    _, proposal, approval, _ = prepared(client)
    url = f"/api/review/proposals/{proposal['id']}"
    assert (
        client.post(url + "/reject", json={"reason": "Review needs another capture"}).status_code
        == 200
    )
    assert client.post(url + "/approve", json=approval).status_code == 409


def test_approval_cannot_supply_actor_or_substitute_amount(review):
    client, _ = review
    _, proposal, approval, _ = prepared(client)
    approval.update(actor_id="admin", amount_minor=1)
    assert (
        client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).status_code
        == 422
    )


def test_expired_proposal_cannot_be_approved(review):
    client, engine = review
    _, proposal, approval, _ = prepared(client)
    with Session(engine) as db, db.begin():
        db.get(Proposal, proposal["id"]).expires_at = time.time() - 1
    assert (
        client.post(f"/api/review/proposals/{proposal['id']}/approve", json=approval).status_code
        == 409
    )


@pytest.mark.parametrize(
    "action", ["refund_capture", "refund_offer", "return_refund_offer", "accept_claim"]
)
def test_all_financial_action_types_require_explicit_review(review, action):
    client, engine = review
    case, _, _, body = prepared(client)
    body["financial_action"]["action"] = action
    body["financial_action"]["target_id"] = (
        "manual-test-capture" if action == "refund_capture" else "manual-test-dispute"
    )
    response = client.post(f"/api/review/cases/{case['id']}/proposals", json=body)
    assert response.status_code == 201
    proposal = response.json()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Outbox)) == 0
    assert proposal["requires_approval"] is True
    result = client.post(
        f"/api/review/proposals/{proposal['id']}/approve",
        json={
            "expected_payload_hash": proposal["payload_hash"],
            "expected_case_version": case["version"],
            "confirm": True,
        },
    )
    assert result.status_code == 200
    assert result.json()["paypal_executed"] is False
    assert len(result.json()["request_id"]) == 32
