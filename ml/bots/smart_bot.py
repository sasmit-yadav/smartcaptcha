"""
Smart Bot - adds random delays and slight jitter to appear more human-like.
Expected telemetry signature:
- Randomized delays (gaussian distribution)
- Slight mouse jitter (±5px deviations)
- Varying typing speed
- Still detectable as bot due to statistical patterns
"""
from base_bot import BaseBot
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import random


class SmartBot(BaseBot):
    """Bot with randomized behavior to appear more human-like."""
    
    def __init__(self, headless=True):
        super().__init__(headless)
        # Gaussian distribution parameters
        self.typing_mean = 0.150  # Mean 150ms per keystroke
        self.typing_std = 0.030   # Std dev 30ms
        self.click_mean = 0.500   # Mean 500ms between clicks
        self.click_std = 0.100    # Std dev 100ms
        self.jitter_range = 5     # ±5px mouse jitter
        
    def get_random_delay(self, mean, std):
        """Get a random delay from gaussian distribution."""
        delay = random.gauss(mean, std)
        return max(0.050, delay)  # Minimum 50ms to avoid negative
        
    def type_with_random_timing(self, element, text):
        """Type text with randomized timing."""
        element.clear()
        for char in text:
            element.send_keys(char)
            delay = self.get_random_delay(self.typing_mean, self.typing_std)
            time.sleep(delay)
            
    def move_with_jitter(self, target_x, target_y):
        """Move mouse with slight random jitter."""
        jitter_x = random.randint(-self.jitter_range, self.jitter_range)
        jitter_y = random.randint(-self.jitter_range, self.jitter_range)
        
        actions = ActionChains(self.driver)
        actions.move_by_offset(target_x + jitter_x, target_y + jitter_y)
        actions.perform()
        
    def run(self):
        """Execute smart bot on quiz page."""
        print("Starting Smart Bot...")
        print(f"Typing: mean={self.typing_mean}s, std={self.typing_std}s")
        print(f"Click: mean={self.click_mean}s, std={self.click_std}s")
        print(f"Jitter: ±{self.jitter_range}px")
        
        try:
            self.start_session()
            self.setup_driver()
            
            # Navigate to quiz page
            self.navigate_to('/quiz.html')
            print("Navigated to quiz page")
            
            # Answer quiz questions with randomized timing
            for i in range(8):  # 8 questions
                print(f"Answering question {i+1}")
                
                # Wait random delay before answering
                delay = self.get_random_delay(self.click_mean, self.click_std)
                time.sleep(delay)
                
                # Add mouse movement with jitter
                jitter_x = random.randint(-self.jitter_range, self.jitter_range)
                jitter_y = random.randint(-self.jitter_range, self.jitter_range)
                self.add_event('mm', x=400 + jitter_x, y=300 + jitter_y, dist=20.5, ang=45.0, vel=180.0, total_dist=200.0)
                
                # Click a random option (0-3)
                option_index = random.randint(0, 3)
                option_btn = self.wait_for_element(By.CSS_SELECTOR, f'.option-btn[data-index="{option_index}"]')
                if option_btn:
                    option_btn.click()
                    # Add click event with randomized timing
                    click_interval = int(self.get_random_delay(self.click_mean, self.click_std) * 1000)
                    self.add_event('cl', x=400 + jitter_x, y=300 + jitter_y, target=f'option-{option_index}', click_interval=click_interval, is_double=False)
                    print(f"Selected option {option_index}")
                
                # Wait random delay before next question
                delay = self.get_random_delay(self.click_mean, self.click_std)
                time.sleep(delay)
                
                # Click next button
                next_btn = self.wait_for_element(By.ID, 'next-btn')
                if next_btn:
                    next_btn.click()
                    self.add_event('cl', x=600, y=500, target='next-button', click_interval=click_interval, is_double=False)
                    print("Clicked next")
            
            # Send events to backend
            self.send_events()
            
            # Wait briefly
            time.sleep(2)
            
            # End session
            self.end_session()
            
            print("Smart Bot completed successfully")
            
        except Exception as e:
            print(f"Smart Bot error: {e}")
        finally:
            self.cleanup()
            
        return self.session_id


if __name__ == "__main__":
    bot = SmartBot(headless=False)
    bot.run()
