from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    print("2. Screenshot initial state...")
    page.screenshot(path='/tmp/multi_1.png', full_page=True)

    print("3. Click field selector...")
    # Use more specific selector - filter-selector contains the field dropdown
    field_select = page.locator('.filter-selector .bk-select').first
    field_select.click()
    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/multi_2_field_dropdown.png', full_page=True)

    # Find options in filter-selector dropdown only
    filter_dropdown = page.locator('.filter-selector .bk-select-dropdown, .filter-selector + * .bk-select-dropdown')
    options_in_filter = page.locator('.filter-selector .bk-option')

    opt_count = options_in_filter.count()
    print(f"   Found {opt_count} options in filter dropdown")

    for i in range(opt_count):
        try:
            text = options_in_filter.nth(i).inner_text()
            bk_id = options_in_filter.nth(i).get_attribute('data-bk-value')
            print(f"   Option {i}: text='{text}', bk-value={bk_id}")
        except Exception as e:
            print(f"   Option {i}: error - {e}")

    # Click 厂商 option
    print("\n4. Clicking 厂商 option...")
    vendor_opt = options_in_filter.filter(has_text="厂商")
    if vendor_opt.count() > 0:
        vendor_opt.click()
        print("   Clicked 厂商")
    else:
        # Try first option if vendor not found
        if opt_count > 0:
            options_in_filter.first.click()
            print("   Clicked first option")

    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/multi_3_after_field.png', full_page=True)

    # Now look for enum dropdown in filter-value section
    print("\n5. Click enum select in filter-value...")
    filter_value = page.locator('.filter-value .bk-select').first
    if filter_value.count() > 0:
        filter_value.click()
        page.wait_for_timeout(1000)
        page.screenshot(path='/tmp/multi_4_enum_dropdown.png', full_page=True)

        # Get enum options
        enum_options = page.locator('.filter-value .bk-select-dropdown .bk-option, .filter-value .bk-option')
        enum_count = enum_options.count()
        print(f"   Found {enum_count} enum options")

        for i in range(enum_count):
            try:
                text = enum_options.nth(i).inner_text()
                bk_id = enum_options.nth(i).get_attribute('data-bk-value')
                print(f"   Enum option {i}: text='{text}', bk-value={bk_id}")
            except Exception as e:
                print(f"   Enum option {i}: error - {e}")

        if enum_count >= 2:
            print("\n6. Select first enum option (Cisco)...")
            enum_options.nth(0).click()
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/multi_5_after_first.png', full_page=True)

            # Check for selected tags
            tags = page.locator('.filter-value .bk-select-tag')
            tag_count = tags.count()
            print(f"   Selected tags: {tag_count}")
            for i in range(tag_count):
                try:
                    tag_text = tags.nth(i).inner_text()
                    print(f"   Tag {i}: {tag_text}")
                except:
                    pass

            print("\n7. Select second enum option (H3C)...")
            # Reopen dropdown
            filter_value.click()
            page.wait_for_timeout(800)

            enum_options = page.locator('.filter-value .bk-select-dropdown .bk-option, .filter-value .bk-option')
            if enum_options.count() >= 2:
                enum_options.nth(1).click()
                page.wait_for_timeout(2500)
                page.screenshot(path='/tmp/multi_6_after_second.png', full_page=True)

                tags = page.locator('.filter-value .bk-select-tag')
                tag_count = tags.count()
                print(f"   Tags after second select: {tag_count}")
                for i in range(tag_count):
                    try:
                        tag_text = tags.nth(i).inner_text()
                        print(f"   Tag {i}: {tag_text}")
                    except:
                        pass

            print("\n8. Verify dropdown options are stable...")
            filter_value.click()
            page.wait_for_timeout(800)

            final_options = page.locator('.filter-value .bk-select-dropdown .bk-option, .filter-value .bk-option')
            final_count = final_options.count()
            print(f"   Final option count: {final_count}")
            print(f"   Options remained stable: {final_count >= enum_count}")

    # Print console logs
    print("\n9. Console logs (last 10):")
    for log in console_logs[-10:]:
        print(f"   {log}")

    print("\n=== Test completed ===")
    browser.close()
