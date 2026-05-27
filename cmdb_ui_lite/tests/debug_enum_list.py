from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

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

    print("\n3. Check enum select Vue component's list property...")
    vue_list = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        return {
            list: vue.$props?.list,
            listType: typeof vue.$props?.list,
            listLength: vue.$props?.list?.length,
            listJSON: JSON.stringify(vue.$props?.list),
            options: vue.$data?.options,
            optionsMap: vue.$data?.optionsMap,
            optionList: vue.$data?.optionList
        };
    }''')
    print(f"   Vue list: {vue_list}")

    # Try forcing render by calling $forceUpdate
    print("\n4. Try forcing Vue update...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (vue) {
            // Force update
            vue.$forceUpdate();
        }
    }''')
    page.wait_for_timeout(1000)

    # Check if options appeared
    options_after = page.evaluate('''() => {
        const options = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(options).slice(0, 10).map(o => o.textContent.trim());
    }''')
    print(f"   Options after force update: {options_after}")

    page.screenshot(path='/tmp/enum_force.png', full_page=True)

    print("\nTest completed!")
    browser.close()
