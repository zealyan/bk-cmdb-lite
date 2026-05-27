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

    print("\n3. Check enum select structure before opening dropdown...")
    enum_structure = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        return {
            selectExists: !!enumSelect,
            selectHTML: enumSelect?.outerHTML || 'not found',
            allChildren: enumSelect ? Array.from(enumSelect.children).map(c => c.tagName + '.' + c.className) : []
        };
    }''')
    print(f"   Structure: {enum_structure}")

    print("\n4. Open enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    print("\n5. Check dropdown after opening...")
    dropdown_structure = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Check for bk-select-dropdown content
        const dropdown = enumSelect?.querySelector('.bk-select-dropdown');
        const dropdownContent = enumSelect?.querySelector('.bk-select-dropdown-content');
        const bkOptions = enumSelect?.querySelector('.bk-options');
        const bkOptionsWrapper = enumSelect?.querySelector('.bk-options-wrapper');

        // Check all bk-option anywhere in enum select
        const allOptions = enumSelect?.querySelectorAll('.bk-option');

        // Check tippy popup (if using external popup)
        const tippyBox = document.querySelector('.tippy-box');
        const tippyContent = document.querySelector('.tippy-content');

        return {
            hasDropdown: !!dropdown,
            hasDropdownContent: !!dropdownContent,
            hasBkOptions: !!bkOptions,
            hasBkOptionsWrapper: !!bkOptionsWrapper,
            bkOptionCount: allOptions?.length || 0,
            hasTippy: !!tippyBox,
            tippyHTML: tippyContent?.innerHTML?.substring(0, 500) || 'none',
            enumSelectHTML: enumSelect?.outerHTML?.substring(0, 1000) || 'not found'
        };
    }''')
    print(f"   Dropdown: {dropdown_structure}")

    page.screenshot(path='/tmp/struct.png', full_page=True)

    # Search entire document for bk-option
    print("\n6. Search entire document for bk-option...")
    all_bk_options = page.evaluate('''() => {
        const allOptions = document.querySelectorAll('.bk-option');
        const result = [];
        allOptions.forEach((opt, i) => {
            if (i < 20) {
                result.push({
                    text: opt.textContent.trim(),
                    parentClass: opt.parentElement?.className || '',
                    grandparentClass: opt.parentElement?.parentElement?.className || ''
                });
            }
        });
        return {
            total: allOptions.length,
            first20: result
        };
    }''')
    print(f"   All bk-options: {all_bk_options}")

    # Check what's inside the dropdown
    print("\n7. Deep dive into dropdown...")
    deep_dropdown = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Get all elements in enumSelect
        const allElements = [];
        const walk = (el, depth) => {
            if (depth > 5) return;
            const children = el.querySelectorAll(':scope > *');
            children.forEach(child => {
                allElements.push({
                    tag: child.tagName,
                    class: child.className,
                    text: child.textContent?.trim()?.substring(0, 50)
                });
                walk(child, depth + 1);
            });
        };
        if (enumSelect) walk(enumSelect, 0);

        return allElements.slice(0, 30);
    }''')
    print(f"   Deep elements: {deep_dropdown}")

    print("\nTest completed!")
    browser.close()
