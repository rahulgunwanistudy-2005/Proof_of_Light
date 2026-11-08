"""SQLAlchemy 2 mappings: https://docs.sqlalchemy.org/en/20/orm/quickstart.html"""

import time
import uuid

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "review_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    merchant_id: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(default=1)
    inputs_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(default=time.time)


class Proposal(Base):
    __tablename__ = "review_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id"), index=True)
    case_version: Mapped[int]
    inputs_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(80), default="merchant-review-1")
    rule: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")
    created_at: Mapped[float] = mapped_column(default=time.time)
    expires_at: Mapped[float]


class Approval(Base):
    __tablename__ = "merchant_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("review_proposals.id"), unique=True)
    actor_id: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    case_version: Mapped[int]
    created_at: Mapped[float] = mapped_column(default=time.time)


class Outbox(Base):
    __tablename__ = "review_outbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("review_proposals.id"), unique=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("merchant_approvals.id"), unique=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="AWAITING_EXECUTOR")
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[float] = mapped_column(default=time.time)


class Audit(Base):
    __tablename__ = "review_audit"
    __table_args__ = (UniqueConstraint("case_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id"), index=True)
    sequence: Mapped[int]
    event: Mapped[dict] = mapped_column(JSON)
    previous_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(default=time.time)
