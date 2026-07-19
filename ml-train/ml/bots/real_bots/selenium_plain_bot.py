"""
Tool-config bot #1: plain Selenium (unmodified, no stealth patches).

Drives REAL mouse movement (ActionChains along a curved path) and REAL
per-character typing (with human-like pacing between characters) against
demo-site's login page, letting the page's own real DOM-event collector
capture everything — no Python-side event fabrication. This is the
"baseline automation tool" case: navigator.webdriver is expected to read
True (Selenium sets it and does nothing to hide it), so the fingerprint
axis should catch this one on its own regardless of how human the timing
looks — the interesting question is whether behavioural signals ALSO catch
it when fingerprint is later hidden by a stealth-patched driver (see
undetected_chromedriver_bot.py).
"""
import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from .common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush
except ImportError:
    from common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush


def _type_with_pacing(element, text):
    """Real per-character send_keys() calls with randomized real sleeps
    between them — the browser's real keydown/keyup listeners see real,
    humanly-paced timestamps; nothing here is fabricated."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.06, 0.18))


def _move_and_click(driver, element):
    """Move to the element with a curved approach, then click.

    Anchors on move_to_element() (absolute, element-relative) rather than
    chaining raw move_by_offset() deltas from an arbitrary start — Selenium's
    relative-offset semantics are ambiguous about what "current position"
    means before any move has happened, and can walk the cursor outside the
    viewport ("move target out of bounds"). Small jitter offsets anchored on
    a known-good absolute position stay safely on-screen.
    """
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.perform()

    for _ in range(3):
        jitter_x = random.randint(-8, 8)
        jitter_y = random.randint(-8, 8)
        try:
            ActionChains(driver).move_to_element_with_offset(
                element, jitter_x, jitter_y
            ).pause(random.uniform(0.03, 0.08)).perform()
        except Exception:
            break  # jitter landed outside the element's box; skip, not fatal

    time.sleep(random.uniform(0.1, 0.3))
    element.click()


def run(headless=True):
    """Run one real-interaction Selenium session. Returns the collector's
    own sessionId (read from the page), or None on failure."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,900")

    driver = webdriver.Chrome(options=options)
    session_id = None
    try:
        driver.set_page_load_timeout(30)
        driver.get(f"{DEMO_SITE_URL}/login.html")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        time.sleep(1.5)  # let session.js register the session

        session_id = driver.execute_script(
            "return sessionStorage.getItem('sc_session_id')"
        )

        email = driver.find_element(By.ID, "email")
        _move_and_click(driver, email)
        _type_with_pacing(email, "selenium.plain@test.com")

        password = driver.find_element(By.ID, "password")
        _move_and_click(driver, password)
        _type_with_pacing(password, "Password123")

        submit = driver.find_element(By.ID, "submit-btn")
        _move_and_click(driver, submit)

        # The page's own script redirects to /quiz.html after ~2.3s,
        # firing beforeunload -> sendTelemetry() with keepalive:true.
        wait_for_telemetry_flush(3.0)
    except Exception as e:
        print(f"[selenium_plain_bot] error: {e}")
    finally:
        driver.quit()

    if session_id:
        label_session(session_id, "bot")
        print(f"[selenium_plain_bot] labeled session {session_id[:8]}...")
    return session_id


if __name__ == "__main__":
    run(headless=True)
