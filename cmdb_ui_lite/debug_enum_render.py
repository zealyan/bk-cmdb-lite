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

    print("\n3. Try clicking enum select and waiting for async render...")

    # Click with mouse
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) {
            // Dispatch a click event
            select.click();
        }
    }''')

    # Wait and check multiple times
    for i in range(5):
        page.wait_for_timeout(500)

        options_count = page.evaluate('''() => {
            // Check multiple possible locations
            const locations = [
                // Inside enum select
                document.querySelectorAll('.filter-value .bk-select .bk-option'),
                // Inside any dropdown related to enum select
                document.querySelectorAll('.filter-value .bk-options .bk-option'),
                // In any popup/dropdown
                document.querySelectorAll('.bk-select-dropdown .bk-option'),
                document.querySelectorAll('.bk-options .bk-option'),
                // Document level
                document.querySelectorAll('.bk-option')
            ];

            return locations.map((opts, i) => opts.length);
        }''')

        print(f"   Attempt {i+1}: options at locations: {options_count}")

        if any(c > 0 for c in options_count):
            print(f"   Found options at attempt {i+1}!")
            break

    # Get all bk-option text
    all_options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.bk-option');
        return Array.from(opts).slice(0, 10).map(o => o.textContent.trim());
    }''')
    print(f"   All bk-option texts: {all_options}")

    # Check if enum select has any rendered options by looking at its full structure
    full_structure = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Get computed styles
        const style = enumSelect ? window.getComputedStyle(enumSelect) : null;

        // Check all elements inside
        const allTags = [];
        if (enumSelect) {
            const all = enumSelect.querySelectorAll('*');
            all.forEach(el => {
                allTags.push({
                    tag: el.tagName,
                    class: el.className
                });
            });
        }

        // Check for hidden elements
        const hidden = [];
        if (enumSelect) {
            const all = enumSelect.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
            all.forEach(el => {
                hidden.push({
                    tag: el.tagName,
                    class: el.className
                });
            });
        }

        return {
            selectExists: !!enumSelect,
            elementCount: enumSelect?.querySelectorAll('*').length || 0,
            style: style ? { display: style.display } : null,
            allTags: allTags.slice(0, 20),
            hiddenCount: hidden.length,
            hidden: hidden.slice(0, 10)
        };
    }''')
    print(f"   Full structure: {full_structure}")

    # Take screenshot
    page.screenshot(path='/tmp/enum_final.png', full_page=True)

    # For comparison, check what the field selector looks like when open
    print("\n4. For comparison - check field selector structure...")
    page.locator('.filter-selector .bk-select').click()
    page.wait_for_timeout(1000)

    field_structure = page.evaluate('''() => {
        const dropdown = document.querySelector('.filter-selector .bk-select-dropdown');
        const options = dropdown?.querySelectorAll('.bk-option');
        const optionsWrapper = dropdown?.querySelector('.bk-options-wrapper');

        return {
            hasDropdown: !!dropdown,
            hasOptionsWrapper: !!optionsWrapper,
            optionCount: options?.length || 0,
            dropdownHTML: dropdown?.innerHTML?.substring(0, 500) || 'none'
        };
    }''')
    print(f"   Field selector: {field_structure}")

    print("\nTest completed!")
    browser.close()
