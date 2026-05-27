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

    # Check enum select before opening dropdown
    print("\n3. Check enum select before opening...")
    enum_before = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        return {
            exists: !!enumSelect,
            hasBkOptionChildren: enumSelect?.querySelectorAll(':scope > bk-option, :scope > Bk-option').length > 0,
            // Check all elements at body level
            bodyDirectChildren: document.body.children.length,
            // Find where bk-options is appended
            bkOptionsLocation: null
        };
    }''')
    print(f"   Before: {enum_before}")

    # Now open the dropdown
    print("\n4. Open enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    # Find where enum options might be
    print("\n5. Search everywhere for enum options...")
    all_search = page.evaluate('''() => {
        // Search all elements
        const results = {
            totalElements: document.querySelectorAll('*').length,
            bkOptionTotal: document.querySelectorAll('.bk-option').length,
            bkOptionsTotal: document.querySelectorAll('.bk-options').length,
            bkSelectDropdownTotal: document.querySelectorAll('.bk-select-dropdown').length,
            // Check all tippy popups
            tippyPopups: document.querySelectorAll('.tippy-popper, .tippy-box, [data-tippy]').length,
            // Check for any element containing vendor names
            vendorElements: []
        };

        // Search for elements containing vendor names
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            const text = el.textContent || '';
            if (text.includes('H3C') || text.includes('Cisco') || text.includes('Huawei')) {
                results.vendorElements.push({
                    tag: el.tagName,
                    class: el.className,
                    text: text.trim().substring(0, 50)
                });
            }
        });

        return results;
    }''')
    print(f"   All search: {all_search}")

    # Get the exact location of bk-options
    print("\n6. Find exact location of bk-options...")
    bk_options_location = page.evaluate('''() => {
        const allOptions = document.querySelectorAll('.bk-options, .bk-option');
        const results = [];

        allOptions.forEach((el, i) => {
            if (i < 10) {
                results.push({
                    tag: el.tagName,
                    class: el.className,
                    parent: el.parentElement?.className || '',
                    grandparent: el.parentElement?.parentElement?.className || '',
                    text: el.textContent.trim().substring(0, 50)
                });
            }
        });

        return results;
    }''')
    print(f"   bk-options location: {bk_options_location}")

    # Check if enum select dropdown opened
    dropdown_state = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        const dropdown = enumSelect?.querySelector('.bk-select-dropdown');

        // Get full dropdown content
        const dropdownContent = dropdown?.innerHTML || '';
        const dropdownRef = dropdown?.querySelector('.bk-tooltip-ref');

        return {
            dropdownExists: !!dropdown,
            dropdownContent: dropdownContent.substring(0, 500),
            hasContent: dropdownRef?.innerHTML?.length > 0
        };
    }''')
    print(f"   Dropdown state: {dropdown_state}")

    page.screenshot(path='/tmp/enum_final.png', full_page=True)

    print("\nTest completed!")
    browser.close()
