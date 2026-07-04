"""
Instant Bot - fills forms instantly with zero typing simulation.
Expected telemetry signature:
- Zero keyboard events
- Zero or minimal mouse movement
- Session duration: < 2 seconds
- Single click event
"""
try:
    from .base_bot import BaseBot
except ImportError:
    from base_bot import BaseBot
from selenium.webdriver.common.by import By
import time


class InstantBot(BaseBot):
    """Bot that fills forms instantly using JavaScript, bypassing typing simulation."""
    
    def __init__(self, headless=True, target='demo'):
        super().__init__(headless, target)
    
    def run(self):
        """Execute instant bot behavior on login page."""
        print("Starting Instant Bot...")
        
        try:
            self.start_session()
            self.setup_driver()
            
            # Navigate to login page
            self.navigate_to('/login.html')
            print("Navigated to login page")
            
            # Add click event (instant bot signature: minimal mouse movement)
            self.add_event('cl', x=400, y=300, target='submit-button')
            
            # Instant form fill using JavaScript (no typing simulation)
            self.driver.execute_script("""
                document.getElementById('email').value = 'bot@test.com';
                document.getElementById('password').value = 'password123';
            """)
            print("Form filled instantly via JavaScript")
            
            # Click submit button immediately (no delay)
            submit_btn = self.wait_for_element(By.CSS_SELECTOR, 'button[type="submit"]')
            if submit_btn:
                submit_btn.click()
                print("Submit button clicked immediately")
            
            # Send events to backend
            self.send_events()
            
            # Wait briefly
            time.sleep(2)
            
            # End session
            self.end_session()
            
            print("Instant Bot completed successfully")
            
        except Exception as e:
            print(f"Instant Bot error: {e}")
        finally:
            self.cleanup()
            
        return self.session_id


if __name__ == "__main__":
    bot = InstantBot(headless=False)
    bot.run()
