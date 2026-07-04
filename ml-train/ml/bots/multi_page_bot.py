"""
Multi-page Bot - targets multiple demo-site pages for richer training data.
Cycles through different page types to generate diverse telemetry patterns.
"""
import random
import time

try:
    from .base_bot import BaseBot
except ImportError:
    from base_bot import BaseBot
from selenium.webdriver.common.by import By


class MultiPageBot(BaseBot):
    """Generate bot telemetry across multiple demo-site pages."""

    DEMO_PAGES = [
        '/index.html',
        '/login.html',
        '/signup.html',
        '/article.html',
        '/memory-game.html',
        '/quiz.html',
        '/survey.html',
        '/typing-test.html',
    ]

    def __init__(self, headless=True, target='demo'):
        super().__init__(headless, target)
        self.typing_speed_range = (80, 200)
        self.pause_chance = 0.15

    def maybe_pause(self):
        if random.random() < self.pause_chance:
            time.sleep(random.uniform(0.3, 1.2))

    def type_text(self, element, text):
        element.clear()
        for char in text:
            self.maybe_pause()
            delay = random.randint(*self.typing_speed_range)
            self.add_event('kd', k='CHAR', iki=delay)
            element.send_keys(char)
            hold = random.randint(40, 120)
            time.sleep(hold / 1000)
            self.add_event('ku', k='CHAR', hold=hold)
            time.sleep(delay / 1000)

    def move_to_element(self, element):
        location = element.location
        size = element.size
        target_x = int(location["x"] + size["width"] / 2)
        target_y = int(location["y"] + size["height"] / 2)
        steps = random.randint(5, 12)
        for i in range(1, steps + 1):
            progress = i / steps
            x = int(target_x * progress)
            y = int(target_y * progress)
            self.add_event('mm', x=x, y=y, dist=15.0, ang=45.0, vel=200.0, total_dist=15.0 * i)
            time.sleep(random.uniform(0.02, 0.08))

    def click_element(self, element, target_name):
        self.move_to_element(element)
        delay = random.randint(150, 500)
        time.sleep(delay / 1000)
        element.click()
        self.add_event('cl', x=element.location["x"], y=element.location["y"], target=target_name, interval=delay)

    def run(self):
        print("Starting Multi-page Bot...")
        try:
            self.start_session()
            self.setup_driver()

            # Pick 3 random pages to visit
            pages_to_visit = random.sample(self.DEMO_PAGES, min(3, len(self.DEMO_PAGES)))
            print(f"Visiting pages: {pages_to_visit}")

            for page in pages_to_visit:
                print(f"\n--- Visiting {page} ---")
                self.navigate_to(page)
                time.sleep(2)

                # Try to interact with common elements
                try:
                    # Look for input fields
                    inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                    if inputs:
                        for inp in inputs[:2]:  # Interact with up to 2 inputs
                            try:
                                if inp.is_displayed() and inp.is_enabled():
                                    inp_type = inp.get_attribute('type')
                                    if inp_type in ['text', 'email', 'password']:
                                        self.click_element(inp, f'input-{inp_type}')
                                        if inp_type != 'password':
                                            self.type_text(inp, 'test')
                                        else:
                                            self.type_text(inp, 'Password123')
                                        time.sleep(0.5)
                            except:
                                pass
                except:
                    pass

                try:
                    # Look for buttons
                    buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                    if buttons:
                        for btn in buttons[:1]:  # Click up to 1 button
                            try:
                                if btn.is_displayed() and btn.is_enabled():
                                    self.click_element(btn, 'button')
                                    time.sleep(0.5)
                                    break
                            except:
                                pass
                except:
                    pass

                time.sleep(1)

            self.send_events()
            time.sleep(1)
            self.end_session()
            print("Multi-page Bot completed successfully")
        except Exception as e:
            print(f"Multi-page Bot error: {e}")
        finally:
            self.cleanup()
        return self.session_id


if __name__ == "__main__":
    bot = MultiPageBot(headless=False)
    bot.run()
