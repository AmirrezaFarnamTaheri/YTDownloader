import time

from playwright.sync_api import expect, sync_playwright


def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Wait for server to start
        time.sleep(3)

        try:
            # Navigate to the app
            page.goto("http://localhost:8550")

            # Wait for load
            page.wait_for_load_state("networkidle")

            # Take screenshot of Download View
            page.screenshot(path="verification_main.png")
            print("Screenshot saved to verification_main.png")

            # Verify some elements exist
            expect(
                page.get_by_text("StreamCatch - Ultimate Downloader")
            ).to_be_visible()
            expect(page.get_by_label("Video URL")).to_be_visible()

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification_error.png")
        finally:
            browser.close()


if __name__ == "__main__":
    verify_frontend()
