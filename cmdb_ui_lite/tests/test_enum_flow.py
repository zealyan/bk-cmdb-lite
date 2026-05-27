from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to home page...")
    page.goto('http://localhost:8080')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    print("2. Take home screenshot...")
    page.screenshot(path='/tmp/home_page.png', full_page=True)

    print("3. Click on 交换机 link...")
    # Find and click the 交换机 link
    switch_link = page.locator('a').filter(has_text="交换机").first
    if switch_link.count() > 0:
        switch_link.click()
        print("   Clicked 交换机 link")
    else:
        # Try finding by text content
        page.locator('text=交换机').first.click()
        print("   Clicked 交换机 by text")

    page.wait_for_timeout(3000)
    page.wait_for_load_state('networkidle')
    page.screenshot(path='/tmp/switch_page.png', full_page=True)

    print("4. Check for filter controls...")
    selects = page.locator('.bk-select').all()
    print(f"   Found {len(selects)} bk-select elements")

    for i, select in enumerate(selects):
        try:
            classes = select.get_attribute('class')
            text = select.inner_text()
            print(f"   Select {i}: classes={classes}, text={text[:80]}")
        except Exception as e:
            print(f"   Select {i}: error - {e}")

    # Try finding filter selector
    filter_sel = page.locator('.filter-selector')
    if filter_sel.count() > 0:
        print("   Found .filter-selector")
        filter_sel.screenshot(path='/tmp/filter_selector.png')

    # Check URL
    print(f"\n   Current URL: {page.url}")

    print("\n5. Console logs:")
    for log in console_logs[-20:]:
        print(f"   {log}")

    print("\nTest completed!")
    browser.close()
