"""Exercise a practice case with Chromium's fake camera and a disposable database."""

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", default="http://127.0.0.1:8011")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
errors = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("POL_BROWSER_EXECUTABLE"),
        headless=True,
        args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
    )
    try:
        merchant = browser.new_context(
            viewport={"width": 1280, "height": 900}, accept_downloads=True
        )
        page = merchant.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{args.base}/merchant")
        page.wait_for_load_state("networkidle")
        page.get_by_label("Merchant access token").fill(os.environ["POL_MERCHANT_TOKEN"])
        page.get_by_role("button", name="Open cases").click()
        page.get_by_role("button", name="Create practice case").click()
        page.get_by_role("button", name="Create buyer link").click()
        invitation = page.get_by_label("Buyer invitation link").input_value()
        buyer = browser.new_context(viewport={"width": 390, "height": 844}, permissions=["camera"])
        claim = buyer.new_page()
        claim.on("pageerror", lambda error: errors.append(str(error)))
        claim.goto(invitation)
        claim.wait_for_load_state("networkidle")
        claim.get_by_label("What happened?").fill(
            "Practice evidence from Chromium's simulated camera."
        )
        claim.get_by_label("I consent to camera capture and local analysis").check()
        claim.get_by_role("button", name="Enable camera", exact=True).click()
        claim.get_by_role("button", name="Start light capture").click()
        expect(claim.get_by_text("Guided capture attached.", exact=False)).to_be_visible(
            timeout=25000
        )
        claim.get_by_label("Share this evidence with the merchant").check()
        claim.get_by_role("button", name="Send evidence").click()
        expect(claim.get_by_text("Evidence sent to the merchant for review.")).to_be_visible()
        claim.screenshot(path=args.output / "buyer-mobile.png", full_page=True)
        assert claim.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("button", name="Refresh cases").click()
        expect(
            page.get_by_text("Practice evidence from Chromium's simulated camera.")
        ).to_be_visible()
        expect(page.get_by_role("img", name="Item evidence submitted by the buyer")).to_be_visible()
        with page.expect_download() as capture:
            page.get_by_role("button", name="Download evidence PDF").click()
        capture.value.save_as(args.output / "practice-evidence.pdf")
        page.get_by_label("Refund amount (USD)").fill("10")
        page.get_by_label("Reason for proposal").fill("Practice partial refund")
        page.get_by_role("button", name="Prepare refund proposal").click()
        approve = page.get_by_role("button", name="Approve exact refund")
        expect(approve).to_be_disabled()
        page.get_by_label("I reviewed the amount and destination.").check()
        approve.click()
        expect(
            page.get_by_role("heading", name="Practice approval saved", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("button", name="Send approved sandbox refund")).to_have_count(0)
        page.screenshot(path=args.output / "merchant-desktop.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        shop = buyer.new_page()
        shop.on("pageerror", lambda error: errors.append(str(error)))
        shop.goto(f"{args.base}/shop")
        shop.wait_for_load_state("networkidle")
        expect(shop.get_by_role("button", name="Continue to PayPal")).to_have_count(3)
        expect(shop.get_by_role("button", name="Continue to PayPal").first).to_be_disabled()
        shop.screenshot(path=args.output / "shop-mobile.png", full_page=True)
        assert shop.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        judges = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
        judge = judges.new_page()
        judge.on("pageerror", lambda error: errors.append(str(error)))
        judge.goto(args.base)
        judge.get_by_role("link", name="Try a practice case").click()
        judge.get_by_role("button", name="Start practice case").click()
        expect(judge.get_by_label("Merchant access token")).to_be_hidden()
        with judge.expect_popup() as buyer_popup:
            judge.get_by_role("link", name="Open buyer form").click()
        sample = buyer_popup.value
        sample.get_by_label("What happened?").fill("The practice mug has a chipped rim.")
        expect(sample.get_by_label("Allow the merchant to send my photo")).to_be_hidden()
        sample.get_by_label("Share this evidence with the merchant").check()
        sample.get_by_role("button", name="Send evidence").click()
        expect(sample.get_by_text("Practice evidence saved.", exact=False)).to_be_visible()
        sample.close()
        judge.reload()
        expect(judge.get_by_text("The practice mug has a chipped rim.")).to_be_visible()
        judge.get_by_label("Refund amount (USD)").fill("12")
        judge.get_by_label("Reason for proposal").fill("Practice adjustment for the chipped rim")
        judge.get_by_role("button", name="Prepare refund proposal").click()
        practice_approval = judge.get_by_role("button", name="Approve exact refund")
        expect(practice_approval).to_be_disabled()
        judge.get_by_label("I reviewed the amount and destination.").check()
        practice_approval.click()
        expect(judge.get_by_role("heading", name="Practice approval saved")).to_be_visible()
        expect(judge.get_by_role("button", name="Send approved sandbox refund")).to_have_count(0)
        assert judge.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        judge.screenshot(path=args.output / "practice-mobile.png", full_page=True)
        assert not errors, errors
    finally:
        browser.close()

report = {
    "browser_flow": "passed",
    "capture": "Chromium simulated camera",
    "merchant_review": "saved",
    "no_login_practice": "passed",
    "evidence_pdf": "downloaded",
    "live_paypal": False,
    "browser_errors": errors,
}
(args.output / "review-browser.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
