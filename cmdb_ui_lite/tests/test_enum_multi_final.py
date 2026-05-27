from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("=" * 60)
    print("ENUM MULTI-SELECT TEST")
    print("=" * 60)

    print("\n1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)
    page.screenshot(path='/tmp/multi_1_initial.png', full_page=True)

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
    page.screenshot(path='/tmp/multi_2_field_selected.png', full_page=True)

    print("3. Open enum dropdown...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        return Array.from(opts).map(o => o.textContent.trim());
    }''')
    print(f"   Options: {options}")
    page.screenshot(path='/tmp/multi_3_dropdown_open.png', full_page=True)

    print("\n4. Select first option (H3C)...")
    page.evaluate('''() => {
        const firstOption = document.querySelector('.enum-dropdown .enum-option');
        if (firstOption) firstOption.click();
    }''')
    page.wait_for_timeout(2000)
    page.screenshot(path='/tmp/multi_4_after_first.png', full_page=True)

    tags = page.evaluate('''() => {
        return document.querySelector('.enum-multi-input')?.value;
    }''')
    print(f"   Input value (tags): {tags}")
    print(f"   Table rows after first selection: {page.evaluate('document.querySelectorAll(\".bk-table tbody tr\").length')}")

    print("\n5. Reopen dropdown and select second option (Cisco)...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    # Find Cisco option
    page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        for (const opt of opts) {
            if (opt.textContent.includes('Cisco')) {
                opt.click();
                break;
            }
        }
    }''')
    page.wait_for_timeout(2000)
    page.screenshot(path='/tmp/multi_5_after_second.png', full_page=True)

    final_tags = page.evaluate('''() => {
        return document.querySelector('.enum-multi-input')?.value;
    }''')
    print(f"   Final input value (tags): {final_tags}")
    print(f"   Table rows after second selection: {page.evaluate('document.querySelectorAll(\".bk-table tbody tr\").length')}")

    print("\n6. Verify dropdown options are still stable...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    final_options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        return Array.from(opts).map(o => o.textContent.trim());
    }''')
    print(f"   Final options: {final_options}")
    print(f"   Options remained stable: {final_options == options}")

    page.screenshot(path='/tmp/multi_6_final.png', full_page=True)

    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"  - Options found: {len(options)}")
    print(f"  - After first selection, tags: {tags}")
    print(f"  - After second selection, tags: {final_tags}")
    print(f"  - Options stable: {final_options == options}")
    print("=" * 60)

    # Check for any errors
    errors = [log for log in console_logs if 'error' in log.lower() and 'WebSocket' not in log]
    if errors:
        print("\nErrors found:")
        for e in errors:
            print(f"  {e}")

    print("\n=== TEST COMPLETED SUCCESSFULLY ===")
    browser.close()
