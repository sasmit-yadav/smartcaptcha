"""
Linear Bot - moves mouse in perfectly straight lines.
Expected telemetry signature:
- Mouse movement angle variance: near 0 (perfectly linear)
- Mouse velocity: perfectly constant
- No micro-corrections or jitter
"""
try:
    from .base_bot import BaseBot
except ImportError:
    from base_bot import BaseBot
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time


class LinearBot(BaseBot):
    """Bot that moves mouse in perfectly straight lines using exact pixel coordinates."""
    
    def __init__(self, headless=True, target='demo'):
        super().__init__(headless, target)
    
    def run(self):
        """Execute linear mouse movement bot on memory game page."""
        print("Starting Linear Bot...")
        
        try:
            self.start_session()
            self.setup_driver()
            
            # Navigate to memory game page
            self.navigate_to('/memory-game.html')
            print("Navigated to memory game page")
            
            # Get the first card and calculate exact coordinates
            card = self.wait_for_element(By.CSS_SELECTOR, '.card')
            if not card:
                print("Card not found")
                return None
                
            # Get exact position
            location = card.location
            size = card.size
            target_x = location['x'] + size['width'] // 2
            target_y = location['y'] + size['height'] // 2
            
            print(f"Target coordinates: ({target_x}, {target_y})")
            
            # Add linear mouse movement events (perfectly straight line)
            # Linear bot signature: constant velocity, zero angle variance
            steps = 10
            for i in range(steps):
                progress = (i + 1) / steps
                x = int(target_x * progress)
                y = int(target_y * progress)
                self.add_event('mm', x=x, y=y, dist=16.3, ang=0.0, vel=250.0, total_dist=16.3 * (i + 1))
            
            # Add click event at exact coordinates
            self.add_event('cl', x=target_x, y=target_y, target='card', click_interval=500, is_double=False)
            
            # Move mouse in perfectly straight line to target
            actions = ActionChains(self.driver)
            actions.move_by_offset(target_x, target_y)
            actions.perform()
            print(f"Mouse moved linearly to target")
            
            # Click precisely at coordinates
            actions.click()
            actions.perform()
            print("Clicked at exact coordinates")
            
            # Send events to backend
            self.send_events()
            
            # Wait briefly
            time.sleep(2)
            
            # End session
            self.end_session()
            
            print("Linear Bot completed successfully")
            
        except Exception as e:
            print(f"Linear Bot error: {e}")
        finally:
            self.cleanup()
            
        return self.session_id


if __name__ == "__main__":
    bot = LinearBot(headless=False)
    bot.run()
