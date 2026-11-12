from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Action(StrEnum):
    REFUND_CAPTURE = "refund_capture"
    REFUND_OFFER = "refund_offer"
    RETURN_REFUND_OFFER = "return_refund_offer"
    ACCEPT_CLAIM = "accept_claim"


class CaseSnapshot(StrictModel):
    source: Literal["manual_local_review"] = "manual_local_review"
    paypal_order_id: str = Field(min_length=1, max_length=100)
    capture_id: str | None = Field(default=None, max_length=100)
    dispute_id: str | None = Field(default=None, max_length=100)
    amount_minor: int = Field(gt=0, le=100_000_000, strict=True)
    currency: str = Field(pattern="^[A-Z]{3}$")
    claim_text: str = Field(default="", max_length=8000)
    light_response: str = Field(default="NOT_RECORDED", max_length=40)
    assessment: dict = Field(default_factory=dict)
    evidence_id: str | None = Field(default=None, max_length=36)
    provider_dispute: dict = Field(default_factory=dict)
    shipment: dict = Field(default_factory=dict)


class FinancialAction(StrictModel):
    action: Action
    amount_minor: int = Field(gt=0, le=100_000_000, strict=True)
    currency: str = Field(pattern="^[A-Z]{3}$")
    # Merchant cannot substitute an arbitrary destination; service binds this to
    # the case snapshot. The executor will additionally enforce API stage rules.
    target_id: str = Field(min_length=1, max_length=100)


class Propose(StrictModel):
    financial_action: FinancialAction
    explanation: str = Field(min_length=1, max_length=2000)


class Approve(StrictModel):
    expected_payload_hash: str = Field(pattern="^[a-f0-9]{64}$")
    expected_case_version: int = Field(gt=0, strict=True)
    confirm: bool = Field(strict=True)


class Reject(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)
