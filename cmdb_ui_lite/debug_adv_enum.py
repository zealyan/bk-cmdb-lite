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

    print("3. Check for enum-type property in advanced filter...")
    filter_rows = page.evaluate('''() => {
        const items = document.querySelectorAll('.filter-item');
        const results = [];

        items.forEach((item, i) => {
            const label = item.querySelector('.item-label');
            const text = label.textContent || '';
            if (text.includes('厂商')) {
                const bkSelect = item.querySelector('.bk-select');
                const vue = bkSelect.__vue__;
                results.push({
                    index: i,
                    label: text.trim(),
                    hasSelect: !!bkSelect,
                    vueProps: vue ? Object.keys(vue.$props || {}) : [],
                    list: vue.$props.list,
                    options: vue.$props.options
                });
            }
        });

        return results;
    }''')
    print(f"   Filter rows with 厂商: {filter_rows}")

    # Try clicking operator select
    print("4. Click operator select...")
    page.evaluate('''() => {
        const select = document.querySelector('.item-operator .bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(1000)

    options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(opts).map(o => o.textContent.trim()).slice(0, 10);
    }''')
    print(f"   Operator options: {options}")

    page.screenshot(path='/tmp/adv_enum.png', full_page=True)

    print("Test completed!")
    browser.close()
