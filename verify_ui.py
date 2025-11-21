import time
from playwright.sync_api import sync_playwright


def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to Flet web interface
            page.goto("http://localhost:8550")

            # Wait for app to load blindly since selectors are flaky on canvas
            time.sleep(5)

            # Screenshot 1: Main View
            page.screenshot(path="screenshot_main.png")
            print("Screenshot 1: Main View captured.")

            # Screenshot 2: Advanced Tab
            # Try clicking based on text content, which usually works even if flaky
            try:
                page.get_by_text("Advanced").click()
                time.sleep(1)
                page.screenshot(path="screenshot_advanced.png")
                print("Screenshot 2: Advanced Tab captured.")
            except Exception as e:
                print(f"Could not click Advanced: {e}")

            # Screenshot 3: Settings Tab
            try:
                page.get_by_text("Settings").click()
                time.sleep(1)
                page.screenshot(path="screenshot_settings.png")
                print("Screenshot 3: Settings Tab captured.")
            except Exception as e:
                print(f"Could not click Settings: {e}")

            # Screenshot 4: Queue Tab
            try:
                page.get_by_text("Queue").click()
                time.sleep(1)
                page.screenshot(path="screenshot_queue.png")
                print("Screenshot 4: Queue Tab captured.")
            except Exception as e:
                print(f"Could not click Queue: {e}")

        except Exception as e:
            print(f"Verification script error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    verify_ui()
