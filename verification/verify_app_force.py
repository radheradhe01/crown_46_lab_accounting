from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto("http://0.0.0.0:7860")
        page.wait_for_load_state("networkidle")

        # Take screenshot of default view (Process Data)
        page.screenshot(path="verification/tab_process.png")
        print("Captured Process Data tab")

        # Try to switch tab using role locator
        try:
            page.get_by_role("tab", name="File Archive").click(force=True)
            page.wait_for_timeout(1000)
            page.screenshot(path="verification/tab_archive.png")
            print("Captured File Archive tab")
        except Exception as e:
            print(f"Could not switch tab: {e}")

        browser.close()

if __name__ == "__main__":
    run()
