from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Click field selector and select 厂商...")
    page.locator('.filter-selector .bk-select').click()
    page.wait_for_timeout(1000)

    # Click 厂商
    page.evaluate('''() => {
        const options = document.querySelectorAll('.bk-options .bk-option');
        for (const opt of options) {
            if (opt.textContent.includes('厂商')) {
                opt.click();
                break;
            }
        }
    }''')
    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/f1_vendor.png', full_page=True)

    # Verify enum select appeared
    has_enum = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        return filterValue?.querySelector('.bk-select') !== null;
    }''')
    print(f"   Enum select appeared: {has_enum}")

    print("\n3. Click enum select to open dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/f2_enum_open.png', full_page=True)

    # Get enum options - wait for them to appear
    enum_options = []
    for attempt in range(3):
        enum_options = page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            return Array.from(options).map((opt, i) => ({
                index: i,
                text: opt.textContent.trim(),
                value: opt.getAttribute('data-bk-value')
            }));
        }''')
        if len(enum_options) > 0:
            break
        page.wait_for_timeout(500)

    print(f"   Enum options found: {enum_options}")

    if len(enum_options) >= 2:
        print("\n4. Selecting first enum option (Cisco)...")
        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            if (options.length > 0) options[0].click();
        }''')
        page.wait_for_timeout(2500)
        page.screenshot(path='/tmp/f3_first.png', full_page=True)

        # Check selected tags
        tags = page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
            return Array.from(tags).map(t => t.textContent.trim());
        }''')
        print(f"   Selected tags: {tags}")

        # Check table results
        table_rows = page.evaluate('''() => {
            return document.querySelectorAll('.bk-table .bk-table-body-wrapper tbody tr').length;
        }''')
        print(f"   Table rows: {table_rows}")

        print("\n5. Selecting second enum option (H3C)...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue?.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1000)

        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            if (options.length > 1) options[1].click();
        }''')
        page.wait_for_timeout(2500)
        page.screenshot(path='/tmp/f4_second.png', full_page=True)

        final_tags = page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
            return Array.from(tags).map(t => t.textContent.trim());
        }''')
        print(f"   Final tags: {final_tags}")

        final_rows = page.evaluate('''() => {
            return document.querySelectorAll('.bk-table .bk-table-body-wrapper tbody tr').length;
        }''')
        print(f"   Final table rows: {final_rows}")

        print("\n6. Verifying dropdown options are stable...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue?.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1500)

        final_options = page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            return options.length;
        }''')
        print(f"   Final option count: {final_options}")
        print(f"   Options remained stable: {final_options >= len(enum_options)}")

        page.screenshot(path='/tmp/f5_final.png', full_page=True)

    # Console logs
    print("\n7. Console logs:")
    for log in console_logs[-20:]:
        if 'loadModelData' in log or 'search' in log.lower():
            print(f"   {log}")

    print("\n=== Test completed successfully! ===")
    browser.close()
