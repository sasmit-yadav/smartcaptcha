"""
Aggressive Bot - A new bot type not used in training.
Uses different bot patterns: ultra-fast typing, erratic movements, no pauses.
This bot was NOT used in training the model.
"""
import time
import random
from base_bot import BaseBot


class AggressiveBot(BaseBot):
    """
    Aggressive bot with different patterns than training bots.
    Features:
    - Ultra-fast typing (faster than timed bot)
    - Erratic mouse movements (not linear like linear bot)
    - Zero pauses (unlike stealth bot)
    - High-speed clicking
    """
    
    def __init__(self, headless=False):
        super().__init__(headless)
        self.typing_speed = 30  # ms per character (ultra-fast)
        self.mouse_speed = 50  # ms between movements (very fast)
        self.click_speed = 100  # ms between clicks (very fast)
    
    def type_aggressive(self, element, text):
        """Type text at ultra-fast speed."""
        for char in text:
            time.sleep(self.typing_speed / 1000)
            self.add_event('kd', k=char, tw=self.typing_speed)
            element.send_keys(char)
        
        # Send key up events with minimal hold time
        for char in text:
            self.add_event('ku', k=char, th=20)  # Very short hold
    
    def move_erratic(self, element):
        """Move mouse with erratic, non-linear patterns."""
        location = element.location
        size = element.size
        
        # Target center
        target_x = location['x'] + size['width'] / 2
        target_y = location['y'] + size['height'] / 2
        
        # Add erratic movement events (high velocity, random angles)
        for _ in range(5):
            jitter_x = random.randint(-20, 20)
            jitter_y = random.randint(-20, 20)
            self.add_event('mm', x=int(target_x + jitter_x), y=int(target_y + jitter_y),
                          vel=random.uniform(500, 1000), ang=random.uniform(0, 180))
            time.sleep(self.mouse_speed / 1000)
    
    def click_aggressive(self, element):
        """Click with aggressive timing."""
        self.move_erratic(element)
        time.sleep(self.click_speed / 1000)
        element.click()
        self.add_event('cl', x=element.location['x'], y=element.location['y'],
                      click_interval=self.click_speed)
    
    def run(self):
        """Execute aggressive bot on signup page."""
        print("Starting Aggressive Bot (NEW - not in training data)...")
        print(f"Typing speed: {self.typing_speed}ms per char (ULTRA-FAST)")
        print(f"Mouse speed: {self.mouse_speed}ms (VERY FAST)")
        print(f"Click speed: {self.click_speed}ms (VERY FAST)")
        
        try:
            self.setup_driver()
            
            # Navigate to testing signup page
            self.driver.get("http://localhost:8080/signup.html")
            print("Navigated to testing signup page")
            time.sleep(2)
            
            # Start session
            self.start_session()
            print(f"Session started: {self.session_id}")
            
            # Fill first name with aggressive typing
            fname = self.wait_for_element(By.ID, 'fname')
            if fname:
                self.type_aggressive(fname, 'Aggressive')
                print("Typed first name aggressively")
            
            time.sleep(0.1)  # Minimal delay
            
            # Fill last name with aggressive typing
            lname = self.wait_for_element(By.ID, 'lname')
            if lname:
                self.type_aggressive(lname, 'Bot')
                print("Typed last name aggressively")
            
            time.sleep(0.1)
            
            # Fill email with aggressive typing
            email = self.wait_for_element(By.ID, 'email')
            if email:
                self.type_aggressive(email, 'aggressive@test.com')
                print("Typed email aggressively")
            
            time.sleep(0.1)
            
            # Fill password with aggressive typing
            password = self.wait_for_element(By.ID, 'password')
            if password:
                self.type_aggressive(password, 'Password123')
                print("Typed password aggressively")
            
            time.sleep(0.1)
            
            # Confirm password
            confirm = self.wait_for_element(By.ID, 'confirm')
            if confirm:
                self.type_aggressive(confirm, 'Password123')
                print("Confirmed password aggressively")
            
            time.sleep(0.1)
            
            # Accept terms
            terms = self.wait_for_element(By.ID, 'terms')
            if terms:
                self.click_aggressive(terms)
                print("Accepted terms")
            
            time.sleep(0.05)
            
            # Submit form
            submit = self.wait_for_element(By.ID, 'submit-btn')
            if submit:
                self.click_aggressive(submit)
                print("Submitted form")
            
            # Send events before ending
            self.send_events()
            
            # Wait for result
            time.sleep(3)
            
            # End session
            self.end_session()
            print(f"Session ended: {self.session_id}")
            
            # Check result
            result_box = self.driver.find_element(By.ID, 'result-box')
            if result_box.is_displayed():
                result_text = result_box.text
                print(f"\n=== AGGRESSIVE BOT TEST RESULT ===")
                print(f"{result_text}")
                print(f"===================================")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.driver.quit()


if __name__ == "__main__":
    from selenium.webdriver.common.by import By
    bot = AggressiveBot()
    bot.run()
