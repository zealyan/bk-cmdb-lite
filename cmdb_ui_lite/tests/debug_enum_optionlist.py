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

    print("3. Open enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    print("4. Check optionList ref...")
    option_list = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        const optionListRef = vue.$refs?.optionList;
        const selectDropdownRef = vue.$refs?.selectDropdown;

        return {
            optionListRefExists: !!optionListRef,
            optionListRefType: optionListRef?.constructor?.name,
            optionListRefHTML: optionListRef?.outerHTML?.substring(0, 500),
            selectDropdownExists: !!selectDropdownRef,
            selectDropdownHTML: selectDropdownRef?.outerHTML?.substring(0, 500),
            // Try getting inner elements
            optionListChildren: optionListRef ? Array.from(optionListRef.children).map(c => c.tagName + '.' + c.className) : []
        };
    }''')
    print(f"   Option list: {option_list}")

    # Try clicking on the optionList ref
    print("5. Try clicking optionList...")
    clicked = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        const optionListRef = vue.$refs?.optionList;
        if (!optionListRef) return 'no optionList ref';

        // Get all clickable children
        const children = Array.from(optionListRef.querySelectorAll('*'));
        const clickables = children.filter(c => {
            const text = c.textContent?.trim() || '';
            return text.length > 0 && text.length < 100;
        });

        return {
            totalChildren: children.length,
            clickableCount: clickables.length,
            clickableTexts: clickables.slice(0, 10).map(c => c.textContent.trim())
        };
    }''')
    print(f"   Clickable: {clicked}")

    page.screenshot(path='/tmp/enum_optionlist.png', full_page=True)

    print("Test completed!")
    browser.close()
