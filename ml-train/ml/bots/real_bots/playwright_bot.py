"""
Tool-config bot #2: Playwright (Chromium via CDP, not WebDriver protocol).

Same real-interaction pattern as selenium_plain_bot.py — real mouse.move()
along a curved path and real keyboard.type() with human-like pacing — but
driven through Playwright's CDP-based automation instead of Selenium's
WebDriver protocol. navigator.webdriver still reads True on unpatched
Playwright Chromium, but the underlying automation protocol (CDP directly
vs W3C WebDriver commands relayed through chromedriver) leaves different
low-level traces that some real-world detection stacks distinguish; here
it lets us confirm the model generalizes across tool, not just script.
"""
import random
import time

from playwright.sync_api import sync_playwright

try:
    from .common import DEMO_SITE_URL, curved_path, label_session, wait_for_telemetry_flush
except ImportError:
    from common import DEMO_SITE_URL, curved_path, label_session, wait_for_telemetry_flush


def _type_with_pacing(page, selector, text):
    for char in text:
        page.type(selector, char, delay=0)
        time.sleep(random.uniform(0.06, 0.18))


def _move_and_click(page, selector):
    box = page.locator(selector).bounding_box()
    if not box:
        return
    target = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    start = (random.randint(50, 300), random.randint(50, 300))
    page.mouse.move(*start)
    for point in curved_path(start, target):
        page.mouse.move(*point, steps=2)
        time.sleep(random.uniform(0.01, 0.03))
    time.sleep(random.uniform(0.1, 0.3))
    page.mouse.click(target[0], target[1])


def run(headless=True):
    """Run one real-interaction Playwright session. Returns the collector's
    own sessionId, or None on failure."""
    session_id = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--window-size=1400,900"])
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            page.goto(f"{DEMO_SITE_URL}/login.html", timeout=30000)
            page.wait_for_selector("#email", timeout=10000)
            time.sleep(1.5)  # let session.js register the session

            session_id = page.evaluate("() => sessionStorage.getItem('sc_session_id')")

            _move_and_click(page, "#email")
            _type_with_pacing(page, "#email", "playwright@test.com")

            _move_and_click(page, "#password")
            _type_with_pacing(page, "#password", "Password123")

            _move_and_click(page, "#submit-btn")

            wait_for_telemetry_flush(3.0)
        except Exception as e:
            print(f"[playwright_bot] error: {e}")
        finally:
            browser.close()

    if session_id:
        label_session(session_id, "bot")
        print(f"[playwright_bot] labeled session {session_id[:8]}...")
    return session_id


if __name__ == "__main__":
    run(headless=True)
