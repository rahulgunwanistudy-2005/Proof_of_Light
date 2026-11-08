# Proof of Light: capture assistance for fair refund review

Approved direction, 8 Nov 2026: **capture assistance; money movement stays behind
merchant review.** This supersedes the conflicting fraud-proof and autonomous
refund requirements in the historical `BUILD_BRIEF.md`. That original request
is retained for provenance, not as the current product promise.

## Pitch
Proof of Light helps buyers record clearer item evidence and helps merchants
review refund claims in one place. A guided light sequence measures the uploaded
capture's response; AI organizes visible damage and uncertainty; the merchant
reviews the evidence and explicitly approves each financial action in PayPal.

Pitch line: **Clearer captures. Better-informed refund decisions.**

## Buyer experience
Open a claim invitation, consent, frame the item and order card, and record a
guided capture. Changing lights are optional. Weak response, failure or refusal
leads to recapture or another review/return path, never an automatic denial.
There is no claim that a buyer is committing fraud because a signal fails.

## Merchant experience
Read the PayPal dispute, buyer's explanation, captured frames, light-response
diagnostics and an AI damage suggestion. See uncertainty and known limitations.
Review the exact action, amount, currency and destination. Approve it explicitly
before any refund, refund offer, acceptance, replacement or return commitment.
Changing the proposal or underlying case requires a new approval.

## What the light test means
A match means the uploaded pixels carry the issued sequence under this decoder.
It does not attest a trusted camera, a three-dimensional item, unedited damage,
physical-unit identity or entitlement to a refund. Adaptive injection bypassed
the prototype; a reflective print may also match. Keep that result in the lab.
Replace user-facing VERIFIED/FAILED language with signal matched, signal did
not match, and insufficient signal. Internal versioned reports retain historical
enum names so old exported captures remain reproducible.

## AI and PayPal
AI suggests what is visible and drafts explanations. Code validates proposed
actions. A merchant authorizes money movement. PayPal is the actual sandbox
payment/dispute system; the approval record is not itself a completed PayPal
action. Do not mark a case resolved until an actual API response supports it.
No automatic seller-favor escalation based on the light response.

## Revised gates
The original anti-fraud physics gate failed as a product premise. The user's
chosen pivot permits infrastructure work without representing that gate as
passed. Physical collection remains required before claims about usability or
optical robustness, but is no longer a claim-eligibility or security gate.

1. Foundation: durable case/proposal/approval/outbox records; authenticated
   merchant review; sandbox client and checkout; real dispute ingestion.
2. Assistance: guided capture, AI structured suggestions, evidence package and
   merchant-reviewed actions; no autonomous financial policy.
3. Product UI and lab: make real API status, uncertainty, review and the known
   injection limitation easy to understand.
4. Evaluation, deployment and submission: retain reproducible evidence and
   report the bypass; prove review safeguards and real PayPal behavior.

The original phase budgets and deadline remain planning constraints. Later
milestones must be reported as incomplete until their own real gates pass.
