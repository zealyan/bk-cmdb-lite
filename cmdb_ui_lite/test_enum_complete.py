from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page (fresh load)...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Check if enum select is rendered...")
    # Get filter section structure
    filter_info = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        if (!filterValue) return 'filter-value not found';

        const bkSelects = filterValue.querySelectorAll('.bk-select');
        const searchInput = filterValue.querySelector('.search-input');
        const wrapper = filterValue.querySelector('.search-input-wrapper');

        return {
            bkSelectCount: bkSelects.length,
            hasSearchInput: !!searchInput,
            wrapperHTML: wrapper ? wrapper.outerHTML.substring(0, 500) : 'not found',
            allElements: Array.from(filterValue.querySelectorAll('*')).map(el => el.className).slice(0, 20)
        };
    }''')

    print(f"   Filter info: {filter_info}")

    # Screenshot
    page.screenshot(path='/tmp/test2_initial.png', full_page=True)

    # Get console logs for loading info
    print("\n3. Console logs (loading):")
    for log in console_logs:
        if 'loadModelData' in log or 'enum' in log.lower() or 'property' in log.lower():
            print(f"   {log}")

    # Select vendor field
    print("\n4. Selecting vendor field...")
    page.evaluate('''() => {
        const selects = document.querySelectorAll('.filter-selector .bk-select');
        if (selects.length > 0) selects[0].click();
    }''')
    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/test2_field_dropdown.png', full_page=True)

    # Find vendor option
    vendor_found = page.evaluate('''() => {
        const dropdown = document.querySelector('.filter-selector .bk-select-dropdown');
        if (!dropdown) return { found: false };

        const options = dropdown.querySelectorAll('.bk-option');
        for (let i = 0; i < options.length; i++) {
            if (options[i].textContent.includes('厂商')) {
                options[i].click();
                return { found: true, index: i };
            }
        }
        return { found: false, optionsCount: options.length };
    }''')

    print(f"   Vendor found: {vendor_found}")
    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/test2_after_vendor.png', full_page=True)

    # Check if enum select appeared
    enum_info = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        if (!filterValue) return 'not found';

        const bkSelects = filterValue.querySelectorAll('.bk-select');
        const wrapperHTML = filterValue.querySelector('.search-input-wrapper')?.outerHTML || 'not found';

        return {
            bkSelectCount: bkSelects.length,
            wrapperHTML: wrapperHTML.substring(0, 500)
        };
    }''')

    print(f"\n5. Enum select info: {enum_info}")

    # Click enum select if it exists
    if enum_info.get('bkSelectCount', 0) > 0:
        print("\n6. Clicking enum select dropdown...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1000)
        page.screenshot(path='/tmp/test2_enum_dropdown.png', full_page=True)

        # Get enum options
        enum_options = page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const dropdown = filterValue?.querySelector('.bk-select-dropdown');
            if (!dropdown) return [];

            const options = dropdown.querySelectorAll('.bk-option');
            return Array.from(options).map((opt, i) => ({
                index: i,
                text: opt.textContent.trim(),
                value: opt.getAttribute('data-bk-value')
            }));
        }''')

        print(f"   Enum options: {enum_options}")

        if enum_options:
            print("\n7. Selecting first enum option...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue?.querySelector('.bk-select-dropdown');
                if (dropdown) {
                    const options = dropdown.querySelectorAll('.bk-option');
                    if (options.length > 0) options[0].click();
                }
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/test2_after_first.png', full_page=True)

            # Check tags
            tags = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
                return Array.from(tags).map(t => t.textContent.trim());
            }''')
            print(f"   Selected tags: {tags}")

            print("\n8. Selecting second enum option...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const select = filterValue?.querySelector('.bk-select');
                if (select) select.click();
            }''')
            page.wait_for_timeout(800)

            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue?.querySelector('.bk-select-dropdown');
                if (dropdown) {
                    const options = dropdown.querySelectorAll('.bk-option');
                    if (options.length > 1) options[1].click();
                }
            }''')
            page.wait_for_timeout(2500)
            page.screenshot(path='/tmp/test2_after_second.png', full_page=True)

            final_tags = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const tags = filterValue?.querySelectorAll('.bk-select-tag') || [];
                return Array.from(tags).map(t => t.textContent.trim());
            }''')
            print(f"   Final tags: {final_tags}")

            # Verify dropdown still has options
            print("\n9. Verifying dropdown options are stable...")
            page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const select = filterValue?.querySelector('.bk-select');
                if (select) select.click();
            }''')
            page.wait_for_timeout(800)

            final_options = page.evaluate('''() => {
                const filterValue = document.querySelector('.filter-value');
                const dropdown = filterValue?.querySelector('.bk-select-dropdown');
                if (!dropdown) return 0;
                return dropdown.querySelectorAll('.bk-option').length;
            }''')
            print(f"   Final option count: {final_options}")
            print(f"   Options stable: {final_options >= len(enum_options)}")

    print("\n=== Test completed ===")
    browser.close()
