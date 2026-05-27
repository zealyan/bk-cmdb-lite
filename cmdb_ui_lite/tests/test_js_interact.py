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
    page.screenshot(path='/tmp/js_1.png', full_page=True)

    # Use JS to interact with bk-select
    print("\n3. Use JavaScript to interact with bk-select...")

    # Click the field selector
    page.evaluate('''() => {
        const selects = document.querySelectorAll('.filter-selector .bk-select');
        if (selects.length > 0) {
            selects[0].click();
        }
    }''')
    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/js_2_dropdown.png', full_page=True)

    # Get options using JS
    options_info = page.evaluate('''() => {
        const dropdown = document.querySelector('.filter-selector .bk-select-dropdown');
        if (!dropdown) return { found: false };

        const options = dropdown.querySelectorAll('.bk-option');
        const result = [];
        options.forEach((opt, i) => {
            result.push({
                index: i,
                text: opt.textContent.trim(),
                value: opt.getAttribute('data-bk-value'),
                visible: window.getComputedStyle(opt).display !== 'none'
            });
        });
        return { found: true, count: options.length, options: result };
    }''')

    print(f"   Options found: {options_info}")

    if options_info['found'] and options_info['options']:
        # Click 厂商 option
        for opt in options_info['options']:
            if '厂商' in opt['text']:
                print(f"\n4. Clicking '厂商' option...")
                page.evaluate(f'''() => {{
                    const options = document.querySelectorAll('.filter-selector .bk-option');
                    if (options.length > {opt['index']}) {{
                        options[{opt['index']}].click();
                    }}
                }}''')
                break
        else:
            # Click first option
            print(f"\n4. Clicking first option: {options_info['options'][0]['text']}")
            page.evaluate('''() => {
                const options = document.querySelectorAll('.filter-selector .bk-option');
                if (options.length > 0) options[0].click();
            }''')

        page.wait_for_timeout(1500)
        page.screenshot(path='/tmp/js_3_field_selected.png', full_page=True)

        # Now check for enum dropdown
        print("\n5. Check for enum dropdown...")
        enum_info = page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const selects = filterValue ? filterValue.querySelectorAll('.bk-select') : [];
            return {
                hasSelect: selects.length > 0,
                selectText: selects.length > 0 ? selects[0].textContent.trim() : 'none'
            };
        }''')
        print(f"   Enum select: {enum_info}")

        # Open enum dropdown
        print("\n6. Opening enum dropdown...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            if (filterValue) {
                const select = filterValue.querySelector('.bk-select');
                if (select) select.click();
            }
        }''')
        page.wait_for_timeout(1000)
        page.screenshot(path='/tmp/js_4_enum_dropdown.png', full_page=True)

        # Get enum options
        enum_options_info = page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const dropdown = filterValue ? filterValue.querySelector('.bk-select-dropdown') : null;
            if (!dropdown) return { found: false };

            const options = dropdown.querySelectorAll('.bk-option');
            const result = [];
            options.forEach((opt, i) => {
                result.push({
                    index: i,
                    text: opt.textContent.trim(),
                    value: opt.getAttribute('data-bk-value'),
                    visible: window.getComputedStyle(opt).display !== 'none'
                });
            });
            return { found: true, count: options.length, options: result };
        }''')

        print(f"   Enum options: {enum_options_info}")

        if enum_options_info['found'] and enum_options_info['options']:
            print("\n7. Selecting first enum option...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue ? filterValue.querySelector('.bk-select-dropdown') : null;
                if (dropdown) {
                    const options = dropdown.querySelectorAll('.bk-option');
                    if (options.length > 0) options[0].click();
                }
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/js_5_after_first.png', full_page=True)

            # Check selected tags
            tags_info = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue ? filterValue.querySelectorAll('.bk-select-tag') : [];
                return {
                    count: tags.length,
                    texts: Array.from(tags).map(t => t.textContent.trim())
                };
            }''')
            print(f"   Selected tags: {tags_info}")

            print("\n8. Selecting second enum option...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                if (filterValue) {
                    const select = filterValue.querySelector('.bk-select');
                    if (select) select.click();
                }
            }''')
            page.wait_for_timeout(800)

            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue ? filterValue.querySelector('.bk-select-dropdown') : null;
                if (dropdown) {
                    const options = dropdown.querySelectorAll('.bk-option');
                    if (options.length > 1) options[1].click();
                }
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/js_6_after_second.png', full_page=True)

            # Check final tags
            final_tags = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue ? filterValue.querySelectorAll('.bk-select-tag') : [];
                return {
                    count: tags.length,
                    texts: Array.from(tags).map(t => t.textContent.trim())
                };
            }''')
            print(f"   Final tags: {final_tags}")

            # Verify options still exist
            print("\n9. Verifying dropdown options are stable...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                if (filterValue) {
                    const select = filterValue.querySelector('.bk-select');
                    if (select) select.click();
                }
            }''')
            page.wait_for_timeout(800)

            final_options = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue ? filterValue.querySelector('.bk-select-dropdown') : null;
                if (!dropdown) return 0;
                return dropdown.querySelectorAll('.bk-option').length;
            }''')
            print(f"   Final option count: {final_options}")
            print(f"   Options remained stable: {final_options >= len(enum_options_info['options'])}")

    # Print console logs
    print("\n10. Console logs (errors):")
    for log in console_logs:
        if 'error' in log.lower():
            print(f"    {log}")

    print("\n=== Test completed ===")
    browser.close()
