from playwright.sync_api import sync_playwright, expect
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Set a larger viewport to see everything
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        print("Navigating...")
        page.goto("http://0.0.0.0:7860")
        page.wait_for_load_state("networkidle")

        # Verify Title
        expect(page.get_by_role("heading", name="CSV Data Processor")).to_be_visible()

        # Verify Tabs exist by text
        print("Verifying tabs...")
        page.get_by_text("Process Data").first.click()
        time.sleep(1)
        page.screenshot(path="verification/tab_process.png")

        print("Switching to Archive tab...")
        page.get_by_text("File Archive").click()
        time.sleep(1)
        page.screenshot(path="verification/tab_archive.png")

        print("Done.")
        browser.close()

if __name__ == "__main__":
    run()
