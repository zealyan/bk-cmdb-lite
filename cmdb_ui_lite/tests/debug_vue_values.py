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

    print("3. Open dropdown...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    print("4. Check Vue component state...")
    state = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumWrapper = filterValue?.querySelector('.enum-select-wrapper');

        // Get the wrapper's __vue__ or look for it
        const vueComponent = enumWrapper?.__vue__;

        return {
            wrapperExists: !!enumWrapper,
            hasVue: !!vueComponent,
            vueName: vueComponent?.$options?.name,
            filterValues: vueComponent?.filter?.values,
            filterValue: vueComponent?.filter?.value
        };
    }''')
    print(f"   State: {state}")

    print("\n5. Check filter-values watch...")
    watch_logs = [log for log in console_logs if 'filter.values' in log or 'handleEnumCheckbox' in log]
    print(f"   Watch logs: {watch_logs}")

    print("\n6. Select H3C via direct click...")
    page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        for (const opt of opts) {
            if (opt.textContent.includes('H3C')) {
                const checkbox = opt.querySelector('input');
                console.log('Before click - filter.values:', JSON.stringify(opt.__vue__?.$parent?.filter?.values));
                checkbox.click();
                console.log('After click - filter.values:', JSON.stringify(opt.__vue__?.$parent?.filter?.values));
                break;
            }
        }
    }''')
    page.wait_for_timeout(2000)

    state_after_h3c = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const vueComponent = filterValue?.querySelector('.enum-select-wrapper')?.__vue__;
        return {
            filterValues: vueComponent?.filter?.values,
            filterValue: vueComponent?.filter?.value
        };
    }''')
    print(f"   After H3C: {state_after_h3c}")

    print("\n7. Console logs after H3C:")
    h3c_logs = [log for log in console_logs if 'H3C' in log or 'filter.values' in log or 'handleEnumCheckbox' in log]
    for log in h3c_logs:
        print(f"   {log}")

    print("\n8. Reopen dropdown and select Cisco...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        for (const opt of opts) {
            if (opt.textContent.includes('Cisco')) {
                const checkbox = opt.querySelector('input');
                console.log('Before click Cisco - filter.values:', JSON.stringify(opt.__vue__?.$parent?.filter?.values));
                checkbox.click();
                console.log('After click Cisco - filter.values:', JSON.stringify(opt.__vue__?.$parent?.filter?.values));
                break;
            }
        }
    }''')
    page.wait_for_timeout(2000)

    state_after_cisco = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const vueComponent = filterValue?.querySelector('.enum-select-wrapper')?.__vue__;
        return {
            filterValues: vueComponent?.filter?.values,
            filterValue: vueComponent?.filter?.value
        };
    }''')
    print(f"   After Cisco: {state_after_cisco}")

    print("\n9. All checkbox change logs:")
    checkbox_logs = [log for log in console_logs if 'handleEnumCheckbox' in log]
    for log in checkbox_logs:
        print(f"   {log}")

    page.screenshot(path='/tmp/debug3.png', full_page=True)

    print("\nTest completed!")
    browser.close()
