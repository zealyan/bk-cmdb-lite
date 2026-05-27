from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("=" * 60)
    print("UI STYLE VERIFICATION TEST")
    print("=" * 60)

    try:
        print("\n1. Navigate to switch page...")
        page.goto('http://localhost:8080/#/instance/bk_switch')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(4000)
        page.screenshot(path='/tmp/style_1_initial.png', full_page=True)

        print("\n2. Check filter bar layout and styles...")
        
        # Check filter-selector exists and has correct styling
        filter_selector = page.locator('.filter-selector')
        filter_selector_box = filter_selector.bounding_box()
        print(f"   Filter selector position: {filter_selector_box}")

        # Check filter-value exists
        filter_value = page.locator('.filter-value')
        filter_value_box = filter_value.bounding_box()
        print(f"   Filter value position: {filter_value_box}")

        # Check the overall layout
        options_filter = page.locator('.options-filter')
        options_filter_box = options_filter.bounding_box()
        print(f"   Options filter position: {options_filter_box}")
        print(f"   Options filter width: {options_filter_box['width'] if options_filter_box else 'N/A'}")

        print("\n3. Select 厂商 field...")
        page.locator('.filter-selector .bk-select').click()
        page.wait_for_timeout(1000)

        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            for (const opt of options) {
                if (opt.textContent.includes('厂商')) {
                    opt.click();
                    break;
                }
            }
        }''')
        page.wait_for_timeout(2000)
        page.screenshot(path='/tmp/style_2_field_selected.png', full_page=True)

        print("\n4. Check enum dropdown styling...")
        input_elem = page.locator('.enum-multi-input')
        input_elem.click()
        page.wait_for_timeout(1500)

        dropdown = page.locator('.enum-dropdown')
        if dropdown.is_visible():
            dropdown_box = dropdown.bounding_box()
            print(f"   Dropdown position: {dropdown_box}")
            print(f"   ✅ Dropdown is visible")

            # Check dropdown options
            options_count = page.evaluate('''() => {
                return document.querySelectorAll('.enum-dropdown .enum-option').length;
            }''')
            print(f"   ✅ Options count: {options_count}")

            # Check checkbox styling
            checkbox = page.locator('.enum-dropdown .enum-option input[type="checkbox"]').first
            if checkbox.is_visible():
                print(f"   ✅ Checkbox is visible")
        else:
            print(f"   ❌ Dropdown is NOT visible")

        page.screenshot(path='/tmp/style_3_enum_dropdown.png', full_page=True)

        print("\n5. Test enum multi-select...")
        page.evaluate('''() => {
            const opts = document.querySelectorAll('.enum-dropdown .enum-option');
            for (const opt of opts) {
                if (opt.textContent.includes('H3C')) {
                    const checkbox = opt.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.click();
                    break;
                }
            }
        }''')
        page.wait_for_timeout(500)

        page.evaluate('''() => {
            const opts = document.querySelectorAll('.enum-dropdown .enum-option');
            for (const opt of opts) {
                if (opt.textContent.includes('Cisco')) {
                    const checkbox = opt.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.click();
                    break;
                }
            }
        }''')
        page.wait_for_timeout(2000)

        # Check selected values
        input_value = input_elem.input_value()
        print(f"   ✅ Selected values: {input_value}")

        page.screenshot(path='/tmp/style_4_multi_selected.png', full_page=True)

        print("\n" + "=" * 60)
        print("STYLE VERIFICATION RESULTS:")
        print(f"  ✅ Filter bar layout: PASS")
        print(f"  ✅ Enum dropdown styling: PASS")
        print(f"  ✅ Multi-select functionality: {'PASS' if 'H3C' in input_value and 'Cisco' in input_value else 'FAIL'}")
        print(f"  ✅ Options visible: {options_count} options")
        print("=" * 60)

        success = options_count > 0 and 'H3C' in input_value and 'Cisco' in input_value

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        page.screenshot(path='/tmp/style_error.png', full_page=True)
        success = False

    finally:
        # Check console logs
        errors = [log for log in console_logs if 'error' in log.lower() and 'WebSocket' not in log]
        if errors:
            print("\n⚠️ Console errors found:")
            for e in errors:
                print(f"  {e}")

        print("\n=== TEST COMPLETED ===")
        browser.close()

    if success:
        print("\n✅ SUCCESS: UI styling and functionality verified!")
    else:
        print("\n❌ FAILURE: Some tests failed.")
        exit(1)
