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

    print("\n3. Check enum select for bk-option children...")

    # Check using multiple methods
    result = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Method 1: Direct children
        const directChildren = enumSelect ? Array.from(enumSelect.children) : [];
        const bkOptionsDirect = directChildren.filter(c => c.tagName === 'BK-OPTION');

        // Method 2: All descendants
        const allDescendants = enumSelect ? Array.from(enumSelect.querySelectorAll('*')) : [];
        const bkOptionsAll = allDescendants.filter(c => c.tagName === 'BK-OPTION');

        // Method 3: Check for any element with bk-option class
        const bkOptionClass = enumSelect ? enumSelect.querySelectorAll('[class*="bk-option"]') : [];

        // Method 4: Get raw HTML and search for bk-option
        const rawHTML = enumSelect?.outerHTML || '';
        const hasBkOptionTag = rawHTML.includes('bk-option') || rawHTML.includes('BkOption');

        // Method 5: Get innerHTML
        const innerHTML = enumSelect?.innerHTML || '';

        return {
            directChildrenTags: directChildren.map(c => c.tagName),
            bkOptionsDirectCount: bkOptionsDirect.length,
            bkOptionsAllCount: bkOptionsAll.length,
            bkOptionClassCount: bkOptionClass.length,
            hasBkOptionTag: hasBkOptionTag,
            innerHTMLPreview: innerHTML.substring(0, 500),
            rawHTMLPreview: rawHTML.substring(0, 500)
        };
    }''')

    print(f"   Result: {result}")

    # Also check what Vue sees
    print("\n4. Check Vue internals...")
    vue_check = page.evaluate('''() => {
        // Try to access Vue component
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        if (enumSelect && enumSelect.__vue__) {
            const vm = enumSelect.__vue__;
            return {
                hasVue: true,
                vmName: vm.$options?.name,
                vmProps: vm.$props ? Object.keys(vm.$props) : [],
                vmData: vm._data ? Object.keys(vm._data) : [],
                vmOptions: vm.options
            };
        }

        return { hasVue: false };
    }''')
    print(f"   Vue check: {vue_check}")

    page.screenshot(path='/tmp/enum_check.png', full_page=True)

    print("\nTest completed!")
    browser.close()
