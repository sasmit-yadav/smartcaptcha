"""
Timed Bot - every action has EXACTLY the same delay between them.
Expected telemetry signature:
- Keyboard interval variance: 0 (all exactly 100ms)
- Inter-click timing variance: 0
- Perfectly regular pattern = strong bot signal
"""
try:
    from .base_bot import BaseBot
except ImportError:
    from base_bot import BaseBot
from selenium.webdriver.common.by import By
import time


class TimedBot(BaseBot):
    """Bot that performs actions with EXACTLY fixed timing intervals."""
    
    def __init__(self, headless=True, target='demo', key_delay=0.100, click_delay=0.500):
        super().__init__(headless, target)
        self.key_delay = key_delay  # Exactly 100ms between keystrokes
        self.click_delay = click_delay  # Exactly 500ms between clicks
        
    def type_with_fixed_timing(self, element, text):
        """Type text with EXACTLY the same delay between each character."""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(self.key_delay)  # EXACT delay, no variation
            
    def run(self):
        """Execute timed bot on signup page."""
        print("Starting Timed Bot...")
        print(f"Key delay: {self.key_delay}s, Click delay: {self.click_delay}s")
        
        try:
            self.start_session()
            self.setup_driver()
            
            # Navigate to signup page
            self.navigate_to('/signup.html')
            print("Navigated to signup page")
            
            # Fill first name with fixed timing
            first_name = self.wait_for_element(By.ID, 'fname')
            if first_name:
                self.type_with_fixed_timing(first_name, 'Bot')
                # Add keyboard events with EXACT timing
                for char in 'Bot':
                    self.add_event('kd', k='CHAR', iki=100, hold=50)
                    self.add_event('ku', k='CHAR', iki=100, hold=50)
                print("Typed first name with fixed timing")
            
            time.sleep(self.click_delay)
            
            # Fill last name with fixed timing
            last_name = self.wait_for_element(By.ID, 'lname')
            if last_name:
                self.type_with_fixed_timing(last_name, 'User')
                for char in 'User':
                    self.add_event('kd', k='CHAR', iki=100, hold=50)
                    self.add_event('ku', k='CHAR', iki=100, hold=50)
                print("Typed last name with fixed timing")
            
            time.sleep(self.click_delay)
            
            # Fill email with fixed timing
            email = self.wait_for_element(By.ID, 'email')
            if email:
                self.type_with_fixed_timing(email, 'bot@test.com')
                for char in 'bot@test.com':
                    self.add_event('kd', k='CHAR', iki=100, hold=50)
                    self.add_event('ku', k='CHAR', iki=100, hold=50)
                print("Typed email with fixed timing")
            
            time.sleep(self.click_delay)
            
            # Fill password with fixed timing
            password = self.wait_for_element(By.ID, 'password')
            if password:
                self.type_with_fixed_timing(password, 'Password123')
                for char in 'Password123':
                    self.add_event('kd', k='CHAR', iki=100, hold=50)
                    self.add_event('ku', k='CHAR', iki=100, hold=50)
                print("Typed password with fixed timing")
            
            time.sleep(self.click_delay)
            
            # Click submit with fixed timing
            submit_btn = self.wait_for_element(By.CSS_SELECTOR, 'button[type="submit"]')
            if submit_btn:
                submit_btn.click()
                self.add_event('cl', x=400, y=400, target='submit-button', click_interval=500, is_double=False)
                print("Clicked submit with fixed timing")
            
            # Send events to backend
            self.send_events()
            
            # Wait briefly
            time.sleep(2)
            
            # End session
            self.end_session()
            
            print("Timed Bot completed successfully")
            
        except Exception as e:
            print(f"Timed Bot error: {e}")
        finally:
            self.cleanup()
            
        return self.session_id


if __name__ == "__main__":
    bot = TimedBot(headless=False)
    bot.run()
