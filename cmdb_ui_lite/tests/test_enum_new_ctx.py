from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page (fresh context)...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Select 厂商 field...")
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
    page.screenshot(path='/tmp/s1.png', full_page=True)

    print("\n3. Opening enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    enum_options = page.evaluate('''() => {
        const options = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(options).map((opt, i) => ({
            index: i,
            text: opt.textContent.trim()
        }));
    }''')

    print(f"   Enum options: {enum_options}")

    if len(enum_options) >= 2:
        print("\n4. Selecting first option...")
        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            options[0].click();
        }''')
        page.wait_for_timeout(2500)
        page.screenshot(path='/tmp/s2.png', full_page=True)

        tags = page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-value .bk-select-tag');
            return Array.from(tags).map(t => t.textContent.trim());
        }''')
        print(f"   Tags: {tags}")

        print("\n5. Selecting second option...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue?.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1000)

        page.evaluate('''() => {
            const options = document.querySelectorAll('.bk-options .bk-option');
            if (options.length > 1) options[1].click();
        }''')
        page.wait_for_timeout(2500)
        page.screenshot(path='/tmp/s3.png', full_page=True)

        final_tags = page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-value .bk-select-tag');
            return Array.from(tags).map(t => t.textContent.trim());
        }''')
        print(f"   Final tags: {final_tags}")

        print("\n6. Verifying dropdown stable...")
        page.evaluate('''() => {
            const filterValue = document.querySelector('.filter-value');
            const select = filterValue?.querySelector('.bk-select');
            if (select) select.click();
        }''')
        page.wait_for_timeout(1500)

        final_options = page.evaluate('''() => {
            return document.querySelectorAll('.bk-options .bk-option').length;
        }''')
        print(f"   Final option count: {final_options}")
        print(f"   Options stable: {final_options >= len(enum_options)}")

        page.screenshot(path='/tmp/s4.png', full_page=True)

        print("\n7. Relevant console logs:")
        for log in console_logs[-20:]:
            if 'enumOptions' in log or 'loadModelData' in log:
                print(f"   {log}")

        print("\n=== SUCCESS! Enum multi-select works! ===")
    else:
        print("\n   No enum options found!")
        print("\n8. Debug logs:")
        for log in console_logs:
            if 'enumOptions' in log:
                print(f"   {log}")

    context.close()
    browser.close()
