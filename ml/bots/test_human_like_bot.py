"""
Stealth Bot - A new bot type not used in training.
Combines human-like timing with subtle bot patterns.
This bot was NOT used in training the model.
"""
import time
import random
from base_bot import BaseBot


class StealthBot(BaseBot):
    """
    Stealth bot that mimics human behavior more closely than training bots.
    Features:
    - Variable typing speed (not fixed like timed bot)
    - Slight mouse jitter (not perfect like linear bot)
    - Random pauses (not instant like instant bot)
    - Natural click timing
    """
    
    def __init__(self, headless=False):
        super().__init__(headless)
        self.typing_speed_range = (80, 200)  # ms per character (human-like)
        self.pause_probability = 0.15  # 15% chance to pause
        self.pause_duration_range = (500, 2000)  # ms
        self.mouse_jitter_range = 3  # pixels (subtle jitter)
    
    def type_naturally(self, element, text):
        """Type text with human-like variable speed and pauses."""
        for char in text:
            # Random typing speed
            delay = random.uniform(*self.typing_speed_range) / 1000
            time.sleep(delay)
            
            # Send key event
            self.add_event('kd', k=char, tw=int(delay * 1000))
            element.send_keys(char)
            
            # Random pause (simulating thinking)
            if random.random() < self.pause_probability:
                pause = random.uniform(*self.pause_duration_range) / 1000
                time.sleep(pause)
        
        # Send key up events
        for char in text:
            self.add_event('ku', k=char, th=random.randint(50, 150))
    
    def move_naturally(self, element):
        """Move mouse with subtle human-like jitter (simulated via events)."""
        location = element.location
        size = element.size
        
        # Target center with subtle jitter
        target_x = location['x'] + size['width'] / 2
        target_y = location['y'] + size['height'] / 2
        
        # Add subtle jitter
        jitter_x = random.randint(-self.mouse_jitter_range, self.mouse_jitter_range)
        jitter_y = random.randint(-self.mouse_jitter_range, self.mouse_jitter_range)
        
        # Add mouse movement events (simulated)
        self.add_event('mm', x=int(target_x + jitter_x), y=int(target_y + jitter_y),
                      vel=random.uniform(150, 300), ang=random.uniform(0, 90))
    
    def click_naturally(self, element):
        """Click with human-like timing."""
        self.move_naturally(element)
        
        # Random delay before click
        delay = random.uniform(200, 600) / 1000
        time.sleep(delay)
        
        element.click()
        self.add_event('cl', x=element.location['x'], y=element.location['y'],
                      click_interval=int(delay * 1000))
    
    def run(self):
        """Execute stealth bot on signup page."""
        print("Starting Stealth Bot (NEW - not in training data)...")
        print(f"Typing speed: {self.typing_speed_range}ms per char")
        print(f"Pause probability: {self.pause_probability * 100}%")
        
        try:
            self.setup_driver()
            
            # Navigate to testing signup page
            self.driver.get("http://localhost:8080/signup.html")
            print("Navigated to testing signup page")
            time.sleep(2)
            
            # Start session
            self.start_session()
            print(f"Session started: {self.session_id}")
            
            # Fill first name with natural typing
            fname = self.wait_for_element(By.ID, 'fname')
            if fname:
                self.type_naturally(fname, 'Stealth')
                print("Typed first name naturally")
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Fill last name with natural typing
            lname = self.wait_for_element(By.ID, 'lname')
            if lname:
                self.type_naturally(lname, 'Bot')
                print("Typed last name naturally")
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Fill email with natural typing
            email = self.wait_for_element(By.ID, 'email')
            if email:
                self.type_naturally(email, 'stealth@test.com')
                print("Typed email naturally")
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Fill password with natural typing
            password = self.wait_for_element(By.ID, 'password')
            if password:
                self.type_naturally(password, 'Password123')
                print("Typed password naturally")
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Confirm password
            confirm = self.wait_for_element(By.ID, 'confirm')
            if confirm:
                self.type_naturally(confirm, 'Password123')
                print("Confirmed password naturally")
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Accept terms
            terms = self.wait_for_element(By.ID, 'terms')
            if terms:
                self.click_naturally(terms)
                print("Accepted terms")
            
            time.sleep(random.uniform(0.3, 0.8))
            
            # Submit form
            submit = self.wait_for_element(By.ID, 'submit-btn')
            if submit:
                self.click_naturally(submit)
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
                print(f"\n=== STEALTH BOT TEST RESULT ===")
                print(f"{result_text}")
                print(f"================================")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.driver.quit()


if __name__ == "__main__":
    from selenium.webdriver.common.by import By
    bot = StealthBot()
    bot.run()
