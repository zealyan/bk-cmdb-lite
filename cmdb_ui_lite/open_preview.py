from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    print("Opening web preview...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    # Take screenshot
    screenshot_path = '/tmp/web_preview.png'
    page.screenshot(path=screenshot_path, full_page=False)
    print(f"Screenshot saved to {screenshot_path}")

    print("\n===== WEB PREVIEW READY =====\n")

    # Show page info
    print(f"URL: http://localhost:8080/#/instance/bk_switch")
    print(f"Title: {page.title()}")
    print(f"Page loaded successfully!")

    browser.close()

print("Preview available at: http://localhost:8080/#/instance/bk_switch")
