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
    page.wait_for_timeout(3000)

    print("\n3. Check enum select HTML structure...")
    enum_html = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        return {
            exists: !!enumSelect,
            outerHTML: enumSelect?.outerHTML || 'not found',
            innerHTML: enumSelect?.innerHTML || 'not found'
        };
    }''')
    print(f"   Enum HTML: {enum_html}")

    print("\n4. Open enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    print("\n5. Check enum select after open...")
    enum_after = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');

        // Check all child elements
        const children = [];
        if (enumSelect) {
            const walk = (el, depth) => {
                if (depth > 3) return;
                const childs = Array.from(el.children);
                childs.forEach(c => {
                    children.push({
                        tag: c.tagName,
                        class: c.className,
                        text: c.textContent?.trim()?.substring(0, 100)
                    });
                    walk(c, depth + 1);
                });
            };
            walk(enumSelect, 0);
        }

        // Check for any rendered options
        const options = enumSelect?.querySelectorAll('.bk-option, option, [role="option"]');

        return {
            exists: !!enumSelect,
            children: children,
            optionCount: options?.length || 0,
            outerHTML: enumSelect?.outerHTML?.substring(0, 1000) || 'not found'
        };
    }''')
    print(f"   Enum after open: {enum_after}")

    page.screenshot(path='/tmp/enum_html.png', full_page=True)

    # Get console logs for any errors or warnings
    print("\n6. Console logs:")
    for log in console_logs:
        if 'error' in log.lower() or 'warn' in log.lower() or 'enumOptions' in log:
            print(f"   {log}")

    print("\nTest completed!")
    browser.close()
