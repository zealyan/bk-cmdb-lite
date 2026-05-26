from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("=" * 60)
    print("ENUM MULTI-SELECT FIX VERIFICATION TEST")
    print("=" * 60)

    try:
        print("\n1. Navigate to switch page...")
        page.goto('http://localhost:8080/#/instance/bk_switch')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(4000)
        page.screenshot(path='/tmp/verify_1_initial.png', full_page=True)

        print("2. Select 厂商 field...")
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
        page.screenshot(path='/tmp/verify_2_field_selected.png', full_page=True)

        print("3. Open enum dropdown...")
        input_elem = page.locator('.enum-multi-input')
        input_elem.click()
        page.wait_for_timeout(1500)

        # Get initial options
        options = page.evaluate('''() => {
            const opts = document.querySelectorAll('.enum-dropdown .enum-option');
            return Array.from(opts).map(o => o.textContent.trim());
        }''')
        print(f"   Initial options: {options}")
        page.screenshot(path='/tmp/verify_3_dropdown_open.png', full_page=True)

        print("\n4. Select H3C...")
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
        page.wait_for_timeout(500)  # Short wait for immediate UI update
        page.screenshot(path='/tmp/verify_4_after_h3c.png', full_page=True)

        # Wait for possible search debounce
        page.wait_for_timeout(1500)

        print("\n5. Select Cisco...")
        # Make sure dropdown is still open
        page.evaluate('''() => {
            const input = document.querySelector('.enum-multi-input');
            const dropdown = document.querySelector('.enum-dropdown');
            if (!dropdown || dropdown.style.display === 'none') {
                if (input) input.click();
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
        page.wait_for_timeout(500)  # Short wait for immediate UI update
        page.screenshot(path='/tmp/verify_5_after_cisco.png', full_page=True)

        # Wait for debounce and search to complete
        page.wait_for_timeout(2000)

        print("\n6. Check results...")
        final_tags = input_elem.input_value()
        print(f"   Input value: {final_tags}")

        # Get final options to verify stability
        final_options = page.evaluate('''() => {
            const input = document.querySelector('.enum-multi-input');
            const dropdown = document.querySelector('.enum-dropdown');
            if (!dropdown || dropdown.style.display === 'none') {
                if (input) input.click();
            }
            const opts = document.querySelectorAll('.enum-dropdown .enum-option');
            return Array.from(opts).map(o => o.textContent.trim());
        }''')
        print(f"   Final options: {final_options}")
        print(f"   Options stable: {final_options == options}")

        page.screenshot(path='/tmp/verify_6_final.png', full_page=True)

        print("\n" + "=" * 60)
        print("TEST RESULTS:")
        print(f"  - Initial options found: {len(options)}")
        print(f"  - Input value after two selections: {final_tags}")
        print(f"  - Both H3C and Cisco selected: {'H3C' in final_tags and 'Cisco' in final_tags}")
        print(f"  - Options remained stable: {final_options == options}")
        print("=" * 60)

        success = 'H3C' in final_tags and 'Cisco' in final_tags and (final_options == options)

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        page.screenshot(path='/tmp/verify_error.png', full_page=True)
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
        print("\n✅ SUCCESS: Enum multi-select is working correctly!")
    else:
        print("\n❌ FAILURE: Enum multi-select is not working as expected.")
        exit(1)
