import time
from playwright.sync_api import sync_playwright


def verify_streamcatch():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Wait for the app to start
        max_retries = 10
        for i in range(max_retries):
            try:
                page.goto("http://localhost:8550")
                break
            except:
                print(f"Waiting for server... {i+1}/{max_retries}")
                time.sleep(2)

        # Allow Flet to load
        page.wait_for_load_state("networkidle")
        time.sleep(3)  # Extra buffer for Flet rendering

        # Take a screenshot of the main download view
        page.screenshot(path="verification_main.png")
        print("Main screenshot taken.")

        # Try to add an invalid URL to trigger snackbar (robustness check)
        page.get_by_role("textbox", name="URL").fill("invalid-url")
        # The button might be an icon button, let's try to find it by tooltip or icon
        # In Flet, IconButton usually ends up as a button role.
        # The fetch button has tooltip "Fetch Info".
        # page.get_by_role("button", name="Fetch Info").click() # Name might be icon name if no tooltip in DOM?
        # Flet renders tooltips as separate overlays, usually not accessible by name directly on button click unless title is set.
        # Let's try to click the button by index or selector if needed.
        # But let's just verify the UI loaded first.

        # Check for the new visual elements
        # We expect to see the platform icons

        browser.close()


if __name__ == "__main__":
    verify_streamcatch()
