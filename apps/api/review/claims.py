"""One-use buyer invitations and durable evidence for merchant review."""

import base64
import hashlib
import io
import re
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Header, Request, Response
from PIL import Image, ImageOps
from pydantic import Field, model_validator
from sqlalchemy import select, update

from . import service
from .models import Case, Evidence, Invitation
from .practice_access import PREFIX
from .router import DB, Merchant, Reviewer
from .schemas import CaseSnapshot, StrictModel

router = APIRouter(tags=["claim evidence"])
ClaimToken = Annotated[str, Header(alias="X-Claim-Token", min_length=43, max_length=43)]


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_invitation(db, case, expires_at: float) -> str:
    token = secrets.token_urlsafe(32)
    db.add(Invitation(token_hash=token_hash(token), case_id=case.id, expires_at=expires_at))
    service.audit(db, case, case.merchant_id, "invitation_created", {})
    return f"/claim#{token}"


@router.post("/api/review/cases/{case_id}/invitations", status_code=201)
def invite(case_id: str, db: DB, actor: Merchant):
    with db.begin():
        case = service.case_for_merchant(db, case_id, actor)
        now = time.time()
        db.execute(
            update(Invitation)
            .where(
                Invitation.case_id == case.id,
                Invitation.used_at.is_(None),
                Invitation.expires_at > now,
            )
            .values(expires_at=now)
        )
        path = new_invitation(db, case, now + 7 * 86400)
    return {"path": path}


def get_invitation(db: DB, token: str) -> Invitation:
    invitation = db.get(Invitation, token_hash(token))
    if invitation is None or invitation.expires_at <= time.time():
        raise service.ReviewError(
            "This invitation is invalid or expired. Ask the merchant for a new link.", 404
        )
    return invitation


@router.get("/api/claim")
def invitation_status(db: DB, token: ClaimToken):
    invite_record = get_invitation(db, token)
    case = db.get(Case, invite_record.case_id)
    if case is None:
        raise service.ReviewError("This invitation is invalid or expired.", 404)
    return {
        "submitted": invite_record.used_at is not None,
        "practice": case.merchant_id.startswith(PREFIX),
    }


class Submission(StrictModel):
    statement: str = Field(min_length=1, max_length=8000)
    capture_id: str | None = Field(default=None, max_length=80)
    photo: str | None = Field(default=None, max_length=7_000_000)
    ai_consent: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_evidence(self):
        if not self.statement.strip():
            raise ValueError("Describe what happened to the item")
        if self.capture_id and self.photo:
            raise ValueError("Choose a photo or guided capture")
        return self


def jpeg(raw: bytes) -> bytes:
    """Decode and re-encode to bound size and remove embedded metadata."""
    try:
        with Image.open(io.BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as image:
            if image.width * image.height > 24_000_000:
                raise ValueError("Image too large")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1600, 1600))
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=86)
            return buffer.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise service.ReviewError("Choose a JPEG, PNG or WebP photo under 5 MB.", 422) from exc


@router.post("/api/claim/evidence", status_code=201)
def submit(body: Submission, request: Request, db: DB, token: ClaimToken):
    image, light = None, {}
    with db.begin():
        invitation = get_invitation(db, token)
        if invitation.used_at is not None:
            raise service.ReviewError("Evidence was already submitted for this invitation.")
        if body.capture_id:
            image, light = request.app.state.claim_capture(body.capture_id, token)
        elif body.photo:
            try:
                raw = base64.b64decode(body.photo, validate=True)
            except ValueError as exc:
                raise service.ReviewError("The photo could not be read.", 422) from exc
            if len(raw) > 5 * 1024 * 1024:
                raise service.ReviewError("Choose a photo under 5 MB.", 422)
            image = jpeg(raw)
        case = db.scalar(select(Case).where(Case.id == invitation.case_id).with_for_update())
        if case is None:
            raise service.ReviewError("Case not found", 404)
        practice = case.merchant_id.startswith(PREFIX)
        claimed = db.execute(
            update(Invitation)
            .where(
                Invitation.token_hash == invitation.token_hash,
                Invitation.used_at.is_(None),
                Invitation.expires_at > time.time(),
            )
            .values(used_at=time.time())
        )
        if claimed.rowcount != 1:
            raise service.ReviewError("This invitation is no longer open.")
        record = Evidence(
            case_id=case.id,
            statement=body.statement.strip(),
            image_jpeg=image,
            light_report=light,
            assessment={},
            ai_consent=body.ai_consent and bool(image) and not practice,
        )
        db.add(record)
        db.flush()
        snapshot = CaseSnapshot.model_validate(case.snapshot).model_copy(
            update={
                "claim_text": body.statement.strip(),
                "light_response": light.get("verdict", "NOT_RECORDED"),
                "assessment": {},
                "evidence_id": record.id,
            }
        )
        service.revise_case(db, case.id, case.merchant_id, case.version, snapshot)
        service.audit(
            db,
            case,
            "buyer",
            "evidence_received",
            {
                "evidence_id": record.id,
                "image_sha256": hashlib.sha256(image).hexdigest() if image else None,
                "ai_consent": record.ai_consent,
            },
        )
    message = (
        "Practice evidence saved. Return to the practice case and refresh."
        if practice
        else "Evidence sent to the merchant for review."
    )
    return {"submitted": True, "message": message}


def latest_evidence(db: DB, case_id: str):
    return db.scalar(
        select(Evidence)
        .where(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.desc(), Evidence.id.desc())
        .limit(1)
    )


@router.get("/api/review/cases/{case_id}/evidence")
def evidence(case_id: str, db: DB, actor: Reviewer):
    service.case_for_merchant(db, case_id, actor)
    record = latest_evidence(db, case_id)
    if record is None:
        return None
    return {
        "id": record.id,
        "statement": record.statement,
        "has_image": record.image_jpeg is not None,
        "light_report": record.light_report,
        "assessment": record.assessment,
        "ai_consent": record.ai_consent,
        "created_at": record.created_at,
    }


@router.get("/api/review/cases/{case_id}/evidence/{evidence_id}.jpg")
def evidence_image(case_id: str, evidence_id: str, db: DB, actor: Reviewer):
    service.case_for_merchant(db, case_id, actor)
    record = db.get(Evidence, evidence_id)
    if record is None or record.case_id != case_id or not record.image_jpeg:
        raise service.ReviewError("Evidence image not found", 404)
    return Response(record.image_jpeg, media_type="image/jpeg")


def claim_owner(token: str | None) -> str | None:
    return token_hash(token) if token and re.fullmatch(r"[\w-]{43}", token, re.ASCII) else None
