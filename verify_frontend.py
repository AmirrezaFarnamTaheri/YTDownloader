from playwright.sync_api import sync_playwright
import time

def verify_frontend():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to Flet app
        try:
            page.goto("http://127.0.0.1:8550")
            # Wait for Flutter canvas to load
            # Flet renders on canvas, standard selectors often fail without proper accessibility enabled
            # But Flet text is usually accessible.
            # Let's wait a fixed time to be sure initialization happens
            time.sleep(5)

            # Take screenshot of main download page
            page.screenshot(path="verification_main.png")
            print("Main page screenshot taken.")

            # Navigate to Queue
            # Try force click by coordinates if text selector fails due to flutter rendering issues in headless
            # Navigation rail is on the left.
            # Let's try to find by aria-label if Flet sets it, or just text.
            # If text fails, we might need to use accessibility tree or just wait longer.

            # Just dump accessibility tree to debug if needed, but for now let's assume text is there.
            # Wait for it explicitly
            try:
                page.click("text=Queue", timeout=5000)
            except:
                 print("Could not click 'Queue' text, trying by accessibility label...")
                 # Flet NavigationRailDestination label
                 page.get_by_label("Queue").click()

            time.sleep(2) # Animation wait
            page.screenshot(path="verification_queue.png")
            print("Queue page screenshot taken.")

            # Navigate to History
            page.click("text=History")
            time.sleep(1)
            page.screenshot(path="verification_history.png")
            print("History page screenshot taken.")

            # Navigate to Dashboard
            page.click("text=Dashboard")
            time.sleep(1)
            page.screenshot(path="verification_dashboard.png")
            print("Dashboard page screenshot taken.")

            # Navigate to Settings
            page.click("text=Settings")
            time.sleep(1)
            page.screenshot(path="verification_settings.png")
            print("Settings page screenshot taken.")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_frontend()
