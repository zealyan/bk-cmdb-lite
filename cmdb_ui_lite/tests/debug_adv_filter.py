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

    print("2. Open advanced filter...")
    # Click advanced filter button
    page.evaluate('''() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('高级筛选')) {
                btn.click();
                break;
            }
        }
    }''')
    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/adv_filter.png', full_page=True)

    print("\n3. Check for bk-select in advanced filter...")
    filter_select_info = page.evaluate('''() => {
        // Find the sideslider with advanced filter
        const sideslider = document.querySelector('.bk-sideslider');
        const bkSelects = sideslider?.querySelectorAll('.bk-select');

        const results = [];
        bkSelects?.forEach((sel, i) => {
            const hasBkOption = sel.querySelectorAll('bk-option, .bk-option').length;
            const hasOptionsAttr = sel.getAttribute('options');
            const html = sel.outerHTML.substring(0, 500);

            results.push({
                index: i,
                hasBkOption: hasBkOption,
                hasOptionsAttr: !!hasOptionsAttr,
                htmlPreview: html
            });
        });

        return {
            sidesliderExists: !!sideslider,
            selectCount: bkSelects?.length || 0,
            selects: results
        };
    }''')
    print(f"   Filter select info: {filter_select_info}")

    # Click on a field selector in advanced filter if exists
    if filter_select_info['selectCount'] > 0:
        print("\n4. Click first bk-select in advanced filter...")
        page.evaluate('''() => {
            const sideslider = document.querySelector('.bk-sideslider');
            const bkSelect = sideslider?.querySelector('.bk-select');
            if (bkSelect) bkSelect.click();
        }''')
        page.wait_for_timeout(1000)

        options_info = page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            return Array.from(options).slice(0, 5).map(o => ({
                text: o.textContent.trim(),
                class: o.className
            }));
        }''')
        print(f"   Options in advanced filter: {options_info}")

    print("\n5. Console logs:")
    for log in console_logs[-10:]:
        print(f"   {log}")

    print("\nTest completed!")
    browser.close()
