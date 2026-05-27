from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("1. Navigate...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Open advanced filter...")
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

    print("3. Add a filter item for vendor...")
    # Click add button if exists
    add_btn = page.locator('button:has-text("添加条件"), .filter-add, button:has-text("添加")').first
    if add_btn.count() > 0:
        add_btn.click()
        page.wait_for_timeout(500)

    # Select vendor from dropdown
    field_selects = page.locator('.filter-item .bk-select').first
    if field_selects.count() > 0:
        field_selects.click()
        page.wait_for_timeout(500)

    # Check if vendor is available
    field_options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(opts).map(o => o.textContent.trim());
    }''')
    print(f"   Field options: {field_options}")

    # Click vendor if available
    for opt in field_options:
        if '厂商' in opt:
            page.evaluate(f'''() => {{
                const opts = document.querySelectorAll('.bk-options .bk-option');
                for (const o of opts) {{
                    if (o.textContent.includes('厂商')) {{
                        o.click();
                        break;
                    }}
                }}
            }}''')
            break
    page.wait_for_timeout(1000)

    # Now check the value select for vendor
    value_selects = page.locator('.filter-item .item-value .bk-select').first
    if value_selects.count() > 0:
        value_selects.click()
        page.wait_for_timeout(1000)

        value_options = page.evaluate('''() => {
            const opts = document.querySelectorAll('.bk-options .bk-option');
            return Array.from(opts).map(o => o.textContent.trim());
        }''')
        print(f"   Value options: {value_options}")

    # Check Vue component for the select
    vue_check = page.evaluate('''() => {
        const selects = document.querySelectorAll('.filter-item .item-value .bk-select');
        const results = [];

        selects.forEach((sel, i) => {
            const vue = sel.__vue__;
            if (vue) {
                results.push({
                    index: i,
                    list: vue.$props?.list,
                    listLength: vue.$props?.list?.length,
                    options: vue.$data?.options,
                    optionList: vue.$refs?.optionList?.innerHTML?.substring(0, 200)
                });
            }
        });

        return results;
    }''')
    print(f"   Vue check: {vue_check}")

    page.screenshot(path='/tmp/adv_vendor.png', full_page=True)

    print("Test completed!")
    browser.close()
