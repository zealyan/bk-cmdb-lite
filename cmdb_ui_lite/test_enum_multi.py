from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch instance page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    print("2. Initial screenshot...")
    page.screenshot(path='/tmp/switch_1_initial.png', full_page=True)

    print("3. Click the field selector (交换机名称)...")
    # First bk-select is the field selector
    field_select = page.locator('.filter-selector .bk-select').first
    field_select.click()
    page.wait_for_timeout(800)

    print("4. Looking for 厂商 option...")
    page.screenshot(path='/tmp/switch_2_field_dropdown.png', full_page=True)

    # Get all options
    options = page.locator('.bk-select-dropdown .bk-option')
    opt_count = options.count()
    print(f"   Found {opt_count} options")

    # Find 厂商 option
    vendor_opt = page.locator('.bk-option').filter(has_text="厂商")
    if vendor_opt.count() > 0:
        vendor_opt.click()
        print("   Selected 厂商")
        page.wait_for_timeout(1000)
        page.screenshot(path='/tmp/switch_3_vendor_selected.png', full_page=True)
    else:
        # List all options
        for i in range(min(opt_count, 20)):
            try:
                text = options.nth(i).inner_text()
                print(f"   Option {i}: {text}")
            except:
                pass

        # Try by partial text
        vendor_opt = page.locator('.bk-option:has-text("厂商")')
        if vendor_opt.count() > 0:
            vendor_opt.click()
            print("   Selected 厂商")
            page.wait_for_timeout(1000)
        else:
            print("   厂商 option not found, selecting first option...")
            options.first.click()

    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/switch_4_after_field.png', full_page=True)

    print("5. Click enum select dropdown...")
    # Find the enum/bool select in filter-value
    enum_select = page.locator('.filter-value .bk-select').first
    if enum_select.count() > 0:
        enum_select.click()
        page.wait_for_timeout(800)
        page.screenshot(path='/tmp/switch_5_enum_dropdown.png', full_page=True)

        # Get all enum options
        enum_options = page.locator('.bk-select-dropdown .bk-option')
        enum_count = enum_options.count()
        print(f"   Found {enum_count} enum options")

        for i in range(enum_count):
            try:
                text = enum_options.nth(i).inner_text()
                print(f"   Enum option {i}: {text}")
            except:
                pass

        if enum_count >= 2:
            print("\n6. Select first enum option...")
            enum_options.nth(0).click()
            page.wait_for_timeout(2000)
            page.screenshot(path='/tmp/switch_6_first_enum.png', full_page=True)

            # Check selected tags
            tags = page.locator('.bk-select-tag').all()
            print(f"   Selected tags: {len(tags)}")
            for tag in tags:
                print(f"   Tag: {tag.inner_text()}")

            print("\n7. Select second enum option...")
            enum_select.click()
            page.wait_for_timeout(500)

            enum_options = page.locator('.bk-select-dropdown .bk-option')
            if enum_options.count() >= 2:
                enum_options.nth(1).click()
                page.wait_for_timeout(2000)
                page.screenshot(path='/tmp/switch_7_second_enum.png', full_page=True)

                tags = page.locator('.bk-select-tag').all()
                print(f"   Selected tags after second select: {len(tags)}")
                for tag in tags:
                    print(f"   Tag: {tag.inner_text()}")

            print("\n8. Verify dropdown options still exist...")
            enum_select.click()
            page.wait_for_timeout(500)

            final_options = page.locator('.bk-select-dropdown .bk-option')
            final_count = final_options.count()
            print(f"   Final option count: {final_count}")
            print(f"   Options stable (>= original): {final_count >= enum_count}")
            page.screenshot(path='/tmp/switch_8_final_options.png', full_page=True)

    # Print error logs
    print("\n9. Error logs:")
    for log in console_logs:
        if 'error' in log.lower():
            print(f"   {log}")

    print("\n=== Test completed ===")
    browser.close()
