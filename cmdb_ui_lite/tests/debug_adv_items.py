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

    print("3. List all filter items...")
    items = page.evaluate('''() => {
        const items = document.querySelectorAll('.filter-item');
        return Array.from(items).map(item => {
            const label = item.querySelector('.item-label');
            return label ? label.textContent.trim() : '';
        });
    }''')
    print(f"   Filter items: {items}")

    print("4. Click operator select in first item...")
    page.evaluate('''() => {
        const select = document.querySelector('.item-operator .bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(1000)

    options = page.evaluate('''() => {
        const opts = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(opts).map(o => o.textContent.trim()).slice(0, 10);
    }''')
    print(f"   First operator options: {options}")

    page.screenshot(path='/tmp/adv_items.png', full_page=True)

    print("Test completed!")
    browser.close()
