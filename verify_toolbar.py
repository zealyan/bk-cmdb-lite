from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:3000')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)
    # 截取工具栏区域
    page.screenshot(path='/workspace/toolbar-verify.png', full_page=False)
    browser.close()
print('Screenshot saved to /workspace/toolbar-verify.png')