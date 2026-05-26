from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    print("2. Take screenshot...")
    page.screenshot(path='/tmp/debug_1.png', full_page=True)

    print("3. Click field selector...")
    field_select = page.locator('.filter-selector .bk-select').first
    if field_select.count() > 0:
        field_select.click()
        page.wait_for_timeout(1000)
        page.screenshot(path='/tmp/debug_2_field_dropdown.png', full_page=True)

        # Debug: list all dropdown options
        dropdown = page.locator('.bk-select-dropdown')
        if dropdown.count() > 0:
            dropdown.screenshot(path='/tmp/debug_3_dropdown.png')

            # List all visible options
            all_options = page.locator('.bk-option-content, .bk-options .bk-option, .bk-select-dropdown *')
            print(f"   Found {all_options.count()} dropdown elements")

            # Try clicking by text
            print("\n   Trying to find 厂商 by text...")
            vendor_text = page.locator('text=厂商')
            print(f"   Found {vendor_text.count()} elements with text '厂商'")

        # Click somewhere else to close dropdown
        page.locator('body').click(position={'x': 10, 'y': 10})
        page.wait_for_timeout(500)

    print("4. Try using search input...")
    # Get all inputs
    inputs = page.locator('input').all()
    print(f"   Found {len(inputs)} input elements")
    for i, inp in enumerate(inputs):
        try:
            inp_type = inp.get_attribute('type')
            inp_class = inp.get_attribute('class')
            inp_placeholder = inp.get_attribute('placeholder')
            print(f"   Input {i}: type={inp_type}, class={inp_class}, placeholder={inp_placeholder}")
        except Exception as e:
            print(f"   Input {i}: error - {e}")

    # Try clicking the first bk-option directly
    print("\n5. Try clicking bk-option elements...")
    bk_options = page.locator('.bk-option')
    opt_count = bk_options.count()
    print(f"   Found {opt_count} .bk-option elements")

    for i in range(min(opt_count, 10)):
        try:
            text = bk_options.nth(i).inner_text()
            bk_id = bk_options.nth(i).get_attribute('data-bk-value')
            print(f"   Option {i}: text='{text}', id={bk_id}")
        except Exception as e:
            print(f"   Option {i}: error - {e}")

    print("\n6. Get outer HTML of filter section...")
    filter_section = page.locator('.options-filter')
    if filter_section.count() > 0:
        html = filter_section.inner_html()
        print(f"   HTML preview: {html[:1000]}...")

    print("\nTest completed!")
    browser.close()
