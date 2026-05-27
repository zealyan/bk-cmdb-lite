from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    page.screenshot(path='/tmp/d1_initial.png', full_page=True)

    print("2. Click field selector...")
    # Click using selector
    field_select = page.locator('.filter-selector .bk-select')
    field_select.click()
    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/d2_after_click.png', full_page=True)

    # Check dropdown state
    dropdown_state = page.evaluate('''() => {
        const dropdown = document.querySelector('.filter-selector .bk-select-dropdown');
        if (!dropdown) return 'dropdown not found';

        const isVisible = dropdown.offsetParent !== null;
        const options = dropdown.querySelectorAll('.bk-option');

        return {
            isVisible,
            display: window.getComputedStyle(dropdown).display,
            visibility: window.getComputedStyle(dropdown).visibility,
            opacity: window.getComputedStyle(dropdown).opacity,
            optionsCount: options.length,
            dropdownHTML: dropdown.outerHTML.substring(0, 1000)
        };
    }''')

    print(f"   Dropdown state: {dropdown_state}")

    # List all visible options using page.locator
    print("\n3. Finding visible options...")
    visible_options = page.locator('.bk-select-dropdown .bk-option:visible, .bk-select-dropdown .bk-option')
    opt_count = visible_options.count()
    print(f"   Found {opt_count} options using locator")

    for i in range(min(opt_count, 20)):
        try:
            text = visible_options.nth(i).inner_text()
            print(f"   Option {i}: {text}")
        except:
            pass

    # Try clicking by position
    if opt_count > 0:
        print("\n4. Clicking by text '厂商'...")
        vendor = page.locator('text=厂商').first
        if vendor.count() > 0:
            vendor.click()
            print("   Clicked 厂商")
            page.wait_for_timeout(1500)
            page.screenshot(path='/tmp/d3_after_vendor.png', full_page=True)

            # Check what happened
            filter_html = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                return filterValue ? filterValue.innerHTML.substring(0, 500) : 'not found';
            }''')
            print(f"   Filter value HTML: {filter_html}")

    print("\nTest completed!")
    browser.close()
