"""
Base bot class with shared logic for all bot types.
"""
import time
import random
import requests
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection

load_dotenv()

DEMO_SITE_URL = os.getenv('DEMO_SITE_URL', 'http://localhost:5173')
TESTING_SITE_URL = os.getenv('TESTING_SITE_URL', 'http://localhost:8080')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
API_KEY = os.getenv('API_KEY', 'demo-key')
AUTO_LABEL_BOT_SESSIONS = os.getenv('AUTO_LABEL_BOT_SESSIONS', '1') == '1'


class BaseBot:
    """Base class for all bot types with common functionality."""
    
    def __init__(self, headless=True, target='demo'):
        self.headless = headless
        self.target = target  # 'demo' for demo-site, 'testing' for testing-website
        self.driver = None
        self.session_id = str(uuid.uuid4())
        self.events = []
        self.session_start_time = None
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with options."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        
    def navigate_to(self, path):
        """Navigate to a specific path on the target site (demo or testing)."""
        if self.target == 'demo':
            url = f"{DEMO_SITE_URL}{path}"
        elif self.target == 'testing':
            url = f"{TESTING_SITE_URL}{path}"
        else:
            raise ValueError(f"Unknown target: {self.target}")
        self.driver.get(url)
        time.sleep(3)  # Wait for page to load and SDK to initialize
        
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present on the page."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            print(f"Element not found: {by}={value}")
            return None
            
    def click_element(self, by, value):
        """Click on an element."""
        try:
            element = self.wait_for_element(by, value)
            if element:
                element.click()
                return True
        except Exception as e:
            print(f"Failed to click element: {e}")
        return False
        
    def fill_input(self, by, value, text):
        """Fill an input field with text."""
        try:
            element = self.wait_for_element(by, value)
            if element:
                element.clear()
                element.send_keys(text)
                return True
        except Exception as e:
            print(f"Failed to fill input: {e}")
        return False
        
    def get_session_id(self):
        """Return the session ID (generated locally)."""
        return self.session_id
    
    def start_session(self):
        """Start session via backend API."""
        try:
            self.session_start_time = int(time.time() * 1000)
            meta = {
                'sessionId': self.session_id,
                'userAgent': 'Selenium Bot',
                'deviceType': 'desktop',
                'screenWidth': 1920,
                'screenHeight': 1080,
                'platform': 'Win32'
            }
            
            response = requests.post(
                f"{BACKEND_URL}/api/session/start",
                json={
                    'sessionId': self.session_id,
                    'meta': meta
                },
                headers={'X-API-Key': API_KEY},
                timeout=5
            )
            print(f"Session started: {self.session_id[:8]}...")
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to start session: {e}")
            return False
    
    def add_event(self, event_type, **kwargs):
        """Add an event to the session."""
        event = {
            'type': event_type,
            't': int(time.time() * 1000),
            **kwargs
        }
        self.events.append(event)
    
    def send_events(self):
        """Send all events to backend API."""
        if not self.events:
            return True
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/telemetry",
                json={
                    'sessionId': self.session_id,
                    'meta': {
                        'sessionId': self.session_id,
                        'userAgent': 'Selenium Bot',
                        'deviceType': 'desktop',
                        'screenWidth': 1920,
                        'screenHeight': 1080
                    },
                    'events': self.events,
                    'timestamp': int(time.time() * 1000)
                },
                headers={'X-API-Key': API_KEY},
                timeout=10
            )
            print(f"Sent {len(self.events)} events to backend")
            self.events = []
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send events: {e}")
            return False
    
    def end_session(self):
        """End session via backend API."""
        try:
            duration_ms = int(time.time() * 1000) - self.session_start_time
            response = requests.post(
                f"{BACKEND_URL}/api/session/end",
                json={
                    'sessionId': self.session_id,
                    'duration': duration_ms
                },
                headers={'X-API-Key': API_KEY},
                timeout=5
            )
            print(f"Session ended: {self.session_id[:8]}... (duration: {duration_ms}ms)")
            if response.status_code == 200 and AUTO_LABEL_BOT_SESSIONS:
                self.label_session("bot")
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to end session: {e}")
            return False

    def label_session(self, label):
        """Mark generated bot telemetry so it is eligible for supervised training."""
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET label = %s WHERE id = %s",
                (label, self.session_id),
            )
            conn.commit()
            cursor.close()
            print(f"Session labeled as {label}: {self.session_id[:8]}...")
            return True
        except Exception as e:
            print(f"Failed to label session: {e}")
            return False
        finally:
            if conn:
                release_connection(conn)
        
    def cleanup(self):
        """Close the browser and cleanup resources."""
        if self.driver:
            self.driver.quit()
            
    def run(self):
        """Main bot execution method - to be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement run() method")
