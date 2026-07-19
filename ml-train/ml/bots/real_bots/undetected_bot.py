"""
Tool-config bot #3: undetected-chromedriver (fingerprint-stealth patched).

Same real-interaction pattern (curved mouse path, human-paced typing) as
selenium_plain_bot.py, but driven through undetected-chromedriver, which
specifically patches navigator.webdriver and other automation tells so
they read as absent — the "off-the-shelf stealth kit" category from the
strategy doc (§B.3: puppeteer-stealth / selenium-stealth patch fingerprint
only, not behaviour). This is the deliberately hard case: fingerprint_score
should now read clean (like a real human), so ONLY the behavioural axis
(and, if trained, the anomaly axis) can catch it. If detection now leans
entirely on timing/behaviour matching what a genuine human produces, that's
the honest measure of how much the fingerprint layer alone was carrying.
"""
import random
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from .common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush
except ImportError:
    from common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush


def _type_with_pacing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.06, 0.18))


def _move_and_click(driver, element):
    """See selenium_plain_bot._move_and_click — same anchor-then-jitter
    approach to avoid Selenium's "move target out of bounds" on raw
    chained move_by_offset() deltas."""
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
            break

    time.sleep(random.uniform(0.1, 0.3))
    element.click()


def run(headless=True):
    """Run one real-interaction undetected-chromedriver session. Returns
    the collector's own sessionId, or None on failure."""
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,900")

    # Pin to the installed Chrome's major version — undetected-chromedriver's
    # auto-detection can otherwise fetch a driver build that doesn't match
    # (observed: it grabbed a v151 driver against a locally installed v137
    # Chrome, which refuses the session outright).
    driver = uc.Chrome(options=options, headless=headless, version_main=137)
    session_id = None
    try:
        driver.set_page_load_timeout(30)
        driver.get(f"{DEMO_SITE_URL}/login.html")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        time.sleep(1.5)

        session_id = driver.execute_script(
            "return sessionStorage.getItem('sc_session_id')"
        )
        webdriver_visible = driver.execute_script("return navigator.webdriver")
        print(f"[undetected_bot] navigator.webdriver reads as: {webdriver_visible}")

        email = driver.find_element(By.ID, "email")
        _move_and_click(driver, email)
        _type_with_pacing(email, "stealth.driver@test.com")

        password = driver.find_element(By.ID, "password")
        _move_and_click(driver, password)
        _type_with_pacing(password, "Password123")

        submit = driver.find_element(By.ID, "submit-btn")
        _move_and_click(driver, submit)

        wait_for_telemetry_flush(3.0)
    except Exception as e:
        print(f"[undetected_bot] error: {e}")
    finally:
        driver.quit()

    if session_id:
        label_session(session_id, "bot")
        print(f"[undetected_bot] labeled session {session_id[:8]}...")
    return session_id


if __name__ == "__main__":
    run(headless=True)
