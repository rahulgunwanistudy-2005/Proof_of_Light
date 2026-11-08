"""Local browser QA with Chromium's fake camera, never a physical test."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pass-name", default="pass1")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
screens = root / "design/screenshots"
screens.mkdir(exist_ok=True)
errors = []
checks = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True, args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 1100}, permissions=["camera"], accept_downloads=True
    )
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8000")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Enable camera", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Start light capture")).to_be_disabled()
    page.screenshot(path=str(screens / f"{args.pass_name}-desktop.png"), full_page=True)
    checks.append("Consent is required before camera access")
    page.get_by_label("I consent to camera capture and local analysis.").check()
    page.get_by_role("button", name="Enable camera", exact=True).click()
    expect(page.get_by_role("button", name="Start light capture")).to_be_enabled(timeout=15000)
    page.get_by_role("button", name="Start light capture").click()
    expect(page.locator("#light-field")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#light-field")).to_be_hidden(timeout=3000)
    expect(page.locator("#status")).to_contain_text("Capture stopped")
    checks.append("Escape cancels the sequence and releases the camera")
    page.get_by_role("button", name="Enable camera", exact=True).click()
    expect(page.get_by_role("button", name="Start light capture")).to_be_enabled(timeout=15000)
    page.get_by_role("button", name="Start light capture").click()
    expect(page.locator("#result")).to_be_visible(timeout=25000)
    expect(page.locator("#result")).to_contain_text("No order binding")
    page.screenshot(
        path=str(screens / f"{args.pass_name}-synthetic-camera-result.png"), full_page=True
    )
    with page.expect_download() as download:
        page.get_by_role("link", name="Download capture (.npz)").click()
    download.value.save_as("/tmp/pol-browser-fake-camera.npz")
    checks.append("Fake-camera recording uploads, analyzes, renders a report and exports NPZ")
    checks.append("This fake camera test does not validate the physical gate")
    for width in (360, 390, 768):
        page.set_viewport_size({"width": width, "height": 844})
        page.goto("http://127.0.0.1:8000")
        page.wait_for_load_state("networkidle")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            f"Overflow at {width}"
        )
        page.screenshot(path=str(screens / f"{args.pass_name}-{width}px.png"), full_page=True)
    checks.append("No horizontal overflow at 360, 390 and 768 px")
    page.emulate_media(reduced_motion="reduce")
    page.get_by_role("button", name="I can’t use changing lights").click()
    expect(page.locator("#status")).to_contain_text("No return request or payment is sent")
    checks.append("Alternative path states no return/payment was sent")
    context.close()
    denied = browser.new_context(viewport={"width": 900, "height": 900})
    denied.grant_permissions([])
    denied_page = denied.new_page()
    denied_page.goto("http://127.0.0.1:8000")
    denied_page.wait_for_load_state("networkidle")
    denied_page.get_by_label("I consent to camera capture and local analysis.").check()
    # Deterministic denial without opening a real camera or permission dialog.
    denied_page.evaluate(
        "() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied', 'NotAllowedError'); }; }"
    )
    denied_page.get_by_role("button", name="Enable camera", exact=True).click()
    expect(denied_page.locator("#status")).to_contain_text("Camera access was blocked")
    checks.append("Camera denial gives a recovery instruction")
    denied.close()
    browser.close()
assert not errors, errors
result = {
    "source": "BROWSER_QA_FAKE_CAMERA",
    "physical_validation": False,
    "checks": checks,
    "page_errors": errors,
}
(root / f"eval/reports/2026-11-08-browser-{args.pass_name}.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result, indent=2))
