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

    page.screenshot(path='/tmp/m1.png', full_page=True)

    print("2. Click field selector to open dropdown...")
    field_select = page.locator('.filter-selector .bk-select')
    field_select.click()
    page.wait_for_timeout(1000)

    # Get field options using correct selector
    field_options = page.evaluate('''() => {
        const options = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(options).map((opt, i) => ({
            index: i,
            text: opt.textContent.trim(),
            value: opt.getAttribute('data-bk-value'),
            isSelected: opt.classList.contains('is-selected')
        }));
    }''')

    print(f"   Field options: {field_options}")

    # Click 厂商 option
    vendor_found = False
    for opt in field_options:
        if '厂商' in opt['text']:
            print(f"\n3. Clicking 厂商 option (index {opt['index']})...")
            page.evaluate(f'''() => {{
                const options = document.querySelectorAll('.bk-options .bk-option');
                options[{opt['index']}].click();
            }}''')
            vendor_found = True
            break

    if not vendor_found:
        print("   厂商 not found, clicking first option...")
        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            if (options.length > 0) options[0].click();
        }''')

    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/m2_after_vendor.png', full_page=True)

    # Check if enum select appeared
    enum_info = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const bkSelects = filterValue?.querySelectorAll('.bk-select');
        return {
            hasEnumSelect: bkSelects?.length > 0,
            selectCount: bkSelects?.length || 0
        };
    }''')
    print(f"\n4. Enum select check: {enum_info}")

    if enum_info.get('hasEnumSelect'):
        print("\n5. Click enum select dropdown...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue?.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1000)

        # Get enum options
        enum_options = page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            return Array.from(options).map((opt, i) => ({
                index: i,
                text: opt.textContent.trim(),
                value: opt.getAttribute('data-bk-value')
            }));
        }''')

        print(f"   Enum options: {enum_options}")

        if enum_options and len(enum_options) >= 2:
            print("\n6. Selecting first enum option...")
            page.evaluate('''() => {
                const options = document.querySelectorAll('.bk-options .bk-option');
                options[0].click();
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/m3_after_first.png', full_page=True)

            # Check tags
            tags = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
                return Array.from(tags).map(t => t.textContent.trim());
            }''')
            print(f"   Selected tags: {tags}")

            # Check table results
            table_count = page.evaluate('''() => {
                const rows = document.querySelectorAll('.bk-table .bk-table-body-wrapper tbody tr');
                return rows.length;
            }''')
            print(f"   Table rows: {table_count}")

            print("\n7. Selecting second enum option...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const select = filterValue?.querySelector('.bk-select');
                if (select) select.click();
            }''')
            page.wait_for_timeout(800)

            page.evaluate('''() => {
                const options = document.querySelectorAll('.bk-options .bk-option');
                if (options.length > 1) options[1].click();
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/m4_after_second.png', full_page=True)

            final_tags = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
                return Array.from(tags).map(t => t.textContent.trim());
            }''')
            print(f"   Final tags: {final_tags}")

            # Verify dropdown options are stable
            print("\n8. Verifying dropdown options are stable...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const select = filterValue?.querySelector('.bk-select');
                if (select) select.click();
            }''')
            page.wait_for_timeout(800)

            final_options = page.evaluate('''() => {
                const options = document.querySelectorAll('.bk-options .bk-option');
                return options.length;
            }''')
            print(f"   Final option count: {final_options}")
            print(f"   Options remained stable: {final_options >= len(enum_options)}")

    # Print relevant logs
    print("\n9. Console logs:")
    for log in console_logs[-15:]:
        if 'error' not in log.lower() or console_logs.index(log) > len(console_logs) - 5:
            print(f"   {log}")

    print("\n=== Test completed ===")
    browser.close()
