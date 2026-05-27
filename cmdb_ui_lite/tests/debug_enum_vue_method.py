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

    print("\n3. Check enum select Vue component...")
    vue_component = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        if (!enumSelect) return 'enumSelect not found';

        // Check if it has __vue__ property
        const vue = enumSelect.__vue__;

        return {
            hasVue: !!vue,
            vueName: vue?.$options?.name,
            vueProps: vue ? Object.keys(vue.$props || {}) : [],
            vueData: vue ? Object.keys(vue.$data || {}) : [],
            // Check for options in various places
            optionsInProps: vue?.$props?.options,
            optionsInData: vue?.$data?.options,
            optionsInExt: vue?.$props?.ext,
            optionsInList: vue?.$props?.list,
            optionsInSaveable: vue?.$props?.saveable,
            // Get component definition
            componentDef: vue?.$options?._componentTag
        };
    }''')
    print(f"   Vue component: {vue_component}")

    # Check the entire enum select element attributes
    print("\n4. Check enum select attributes...")
    attributes = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        if (!enumSelect) return 'not found';

        const attrs = {};
        for (const attr of enumSelect.attributes) {
            attrs[attr.name] = attr.value;
        }

        return {
            attributes: attrs,
            attributeCount: Object.keys(attrs).length
        };
    }''')
    print(f"   Attributes: {attributes}")

    # Try calling select's method to see available options
    print("\n5. Try calling bk-select methods...")
    select_methods = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        if (!enumSelect) return 'not found';

        const vue = enumSelect.__vue__;
        if (!vue) return 'no vue';

        // Try to call component methods
        const methods = {
            hasMethodToggle: typeof vue.toggle === 'function',
            hasMethodShow: typeof vue.show === 'function',
            hasMethodOpen: typeof vue.open === 'function',
            hasMethodSetSelected: typeof vue.setSelected === 'function',
            hasMethodSearch: typeof vue.search === 'function'
        };

        return methods;
    }''')
    print(f"   Methods: {select_methods}")

    page.screenshot(path='/tmp/enum_vue.png', full_page=True)

    print("\nTest completed!")
    browser.close()
