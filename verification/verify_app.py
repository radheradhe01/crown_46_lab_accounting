from playwright.sync_api import sync_playwright, expect
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app
        print("Navigating to app...")
        try:
            page.goto("http://0.0.0.0:7860", timeout=10000)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"Failed to load page: {e}")
            browser.close()
            return

        print("Page loaded. Checking title...")
        # Check title
        expect(page).to_have_title("CSV Data Processor")

        print("Checking Tabs...")
        # Check for Tabs
        expect(page.get_by_role("button", name="Process Data")).to_be_visible()
        expect(page.get_by_role("button", name="File Archive")).to_be_visible()

        # Take screenshot of Process Data tab
        print("Taking screenshot of Process Data tab...")
        time.sleep(2) # Wait for animations
        page.screenshot(path="verification/tab_process.png")

        # Switch to File Archive tab
        print("Switching to File Archive tab...")
        page.get_by_role("button", name="File Archive").click()
        time.sleep(1) # Wait for tab switch

        # Take screenshot of File Archive tab
        print("Taking screenshot of File Archive tab...")
        page.screenshot(path="verification/tab_archive.png")

        browser.close()
        print("Done.")

if __name__ == "__main__":
    run()
