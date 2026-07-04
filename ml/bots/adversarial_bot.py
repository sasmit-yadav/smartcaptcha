"""Adversarial training bot with curved movement, edits, and mixed pauses."""
import random
import time

try:
    from .base_bot import BaseBot
except ImportError:
    from base_bot import BaseBot
from selenium.webdriver.common.by import By


class AdversarialBot(BaseBot):
    """Generate harder bot telemetry for V2 training."""

    def __init__(self, headless=True, target='demo'):
        super().__init__(headless, target)
        self.key_delay_range = (70, 260)
        self.hold_range = (45, 180)
        self.pause_chance = 0.12
        self.edit_chance = 0.18

    def maybe_pause(self):
        if random.random() < self.pause_chance:
            time.sleep(random.uniform(0.4, 1.8))

    def type_text(self, element, text):
        element.clear()
        last_up = None
        for char in text:
            self.maybe_pause()
            now = int(time.time() * 1000)
            iki = now - last_up if last_up else None
            self.add_event("kd", k="CHAR", iki=iki)
            element.send_keys(char)
            hold = random.randint(*self.hold_range)
            time.sleep(hold / 1000)
            self.add_event("ku", k="CHAR", hold=hold)
            last_up = int(time.time() * 1000)
            time.sleep(random.randint(*self.key_delay_range) / 1000)

        if random.random() < self.edit_chance:
            now = int(time.time() * 1000)
            iki = now - last_up if last_up else None
            self.add_event("kd", k="Backspace", iki=iki)
            element.send_keys("\b")
            hold = random.randint(*self.hold_range)
            time.sleep(hold / 1000)
            self.add_event("ku", k="Backspace", hold=hold)
            replacement = text[-1]
            self.add_event("kd", k="CHAR", iki=random.randint(*self.key_delay_range))
            element.send_keys(replacement)
            self.add_event("ku", k="CHAR", hold=random.randint(*self.hold_range))

    def move_to_element(self, element):
        location = element.location
        size = element.size
        target_x = int(location["x"] + size["width"] / 2)
        target_y = int(location["y"] + size["height"] / 2)
        start_x = random.randint(80, 500)
        start_y = random.randint(80, 500)
        total = 0.0
        last_x, last_y = start_x, start_y
        steps = random.randint(8, 18)
        last_angle = None

        for i in range(1, steps + 1):
            progress = i / steps
            curve = random.uniform(-24, 24) * (1 - abs(0.5 - progress))
            x = int(start_x + (target_x - start_x) * progress + curve)
            y = int(start_y + (target_y - start_y) * progress - curve / 2)
            dx = x - last_x
            dy = y - last_y
            dist = (dx * dx + dy * dy) ** 0.5
            total += dist
            angle = random.uniform(0, 120)
            if last_angle is not None:
                angle = abs(angle - last_angle)
            last_angle = angle
            delay = random.uniform(0.035, 0.12)
            velocity = dist / delay if delay else 0
            self.add_event(
                "mm",
                x=x,
                y=y,
                dist=round(dist, 1),
                ang=round(angle, 1),
                vel=round(velocity, 1),
                totalDist=round(total, 1),
            )
            last_x, last_y = x, y
            time.sleep(delay)

    def click_element(self, element, target):
        self.move_to_element(element)
        delay_ms = random.randint(180, 900)
        time.sleep(delay_ms / 1000)
        element.click()
        self.add_event(
            "cl",
            x=element.location["x"],
            y=element.location["y"],
            target=target,
            interval=delay_ms,
            double=False,
        )

    def run(self):
        print("Starting Adversarial Bot...")
        try:
            self.start_session()
            self.setup_driver()
            self.navigate_to("/signup.html")

            fields = [
                ("fname", "Avery"),
                ("lname", "Stone"),
                ("email", f"avery{random.randint(1000, 9999)}@test.com"),
                ("password", "Password123"),
                ("confirm", "Password123"),
            ]
            for field_id, value in fields:
                element = self.wait_for_element(By.ID, field_id)
                if element:
                    self.click_element(element, field_id)
                    self.type_text(element, value)

            terms = self.wait_for_element(By.ID, "terms")
            if terms:
                self.click_element(terms, "terms")

            submit = self.wait_for_element(By.ID, "submit-btn")
            if submit:
                self.click_element(submit, "submit")

            self.send_events()
            time.sleep(1)
            self.end_session()
            print("Adversarial Bot completed successfully")
        except Exception as e:
            print(f"Adversarial Bot error: {e}")
        finally:
            self.cleanup()
        return self.session_id


if __name__ == "__main__":
    bot = AdversarialBot(headless=False)
    bot.run()
