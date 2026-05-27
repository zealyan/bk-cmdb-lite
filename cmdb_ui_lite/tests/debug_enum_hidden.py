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

    print("4. Check for hidden options...")
    hidden_check = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Check all elements including hidden ones
        const allElements = enumSelect?.querySelectorAll('*') || [];

        // Check for any element that might contain option text
        const results = {
            totalElements: allElements.length,
            potentialOptions: [],
            hiddenElements: []
        };

        allElements.forEach(el => {
            const text = el.textContent?.trim() || '';
            if (text.length > 0 && text.length < 100) {
                results.potentialOptions.push({
                    tag: el.tagName,
                    class: el.className,
                    text: text.substring(0, 50),
                    visible: el.offsetParent !== null,
                    display: window.getComputedStyle(el).display,
                    opacity: window.getComputedStyle(el).opacity,
                    visibility: window.getComputedStyle(el).visibility
                });
            }

            if (window.getComputedStyle(el).display === 'none' ||
                window.getComputedStyle(el).visibility === 'hidden' ||
                window.getComputedStyle(el).opacity === '0') {
                results.hiddenElements.push({
                    tag: el.tagName,
                    class: el.className,
                    display: window.getComputedStyle(el).display
                });
            }
        });

        // Also check if options are in a portal/popup outside enumSelect
        const allBkOptions = document.querySelectorAll('.bk-option');
        results.externalOptions = Array.from(allBkOptions).map(o => ({
            text: o.textContent.trim(),
            parent: o.parentElement?.className
        }));

        return results;
    }''')
    print(f"   Hidden check: {hidden_check}")

    # Check if bk-select has internal Vue rendering
    print("5. Check bk-select internal state...")
    internal = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const vue = enumSelect?.__vue__;

        if (!vue) return 'no vue';

        // Try to access internal component state
        return {
            optionsInData: vue.$data?.options,
            optionsMapInData: vue.$data?.optionsMap,
            optionListInData: vue.$data?.optionList,
            renderListInData: vue.$data?.renderList,
            selectedInData: vue.$data?.selected,
            // Check for private properties
            hasRenderedOptions: !!vue.$refs?.options,
            refs: vue.$refs ? Object.keys(vue.$refs) : []
        };
    }''')
    print(f"   Internal: {internal}")

    page.screenshot(path='/tmp/enum_hidden.png', full_page=True)

    print("Test completed!")
    browser.close()
