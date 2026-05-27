from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Select 厂商...")
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

    print("3. Test if Vue reactivity is working...")
    test_result = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        // Get current list
        const originalList = vue.$props?.list;

        // Try to force set list via internal method
        const result = {
            originalList: originalList,
            originalListType: typeof originalList,
            dataOptions: vue.$data?.options,
            dataOptionsMap: vue.$data?.optionsMap,
            // Check if there's a watcher for list
            hasWatchedProps: Object.keys(vue._watcher || {}).length,
            // Try triggering update
            canUpdate: typeof vue.$forceUpdate === 'function'
        };

        return result;
    }''')
    print(f"   Test result: {test_result}")

    # Try to manually set options via Vue
    print("4. Try manually setting options...")
    manual_result = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        // Try to set options directly
        vue.$data.options = [
            { id: 'test1', name: 'Test 1' },
            { id: 'test2', name: 'Test 2' }
        ];
        vue.$forceUpdate();

        return {
            dataOptionsSet: vue.$data?.options,
            optionListRefHTML: vue.$refs?.optionList?.innerHTML
        };
    }''')
    print(f"   Manual result: {manual_result}")

    page.wait_for_timeout(1000)

    # Check if options appeared
    options_after = page.evaluate('''() => {
        const opts = document.querySelectorAll('.bk-option');
        return Array.from(opts).map(o => o.textContent.trim());
    }''')
    print(f"   Options after manual set: {options_after}")

    # Print all console logs
    print("5. All console logs:")
    for log in console_logs:
        print(f"   {log}")

    page.screenshot(path='/tmp/manual_set.png', full_page=True)

    print("Test completed!")
    browser.close()
