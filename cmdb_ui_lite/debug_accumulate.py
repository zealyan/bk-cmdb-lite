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

    # Get initial values
    initial = page.evaluate('''() => {
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root;
        let component = null;
        const walk = (v) => {
            if (v?.$options?.name === 'GeneralModel') component = v;
            (v?.$children || []).forEach(walk);
        };
        walk(vm);
        return {
            filterValues: component?.filter?.values,
            filterValue: component?.filter?.value,
            enumDropdownVisible: component?.enumDropdownVisible
        };
    }''')
    print(f"   Initial: {initial}")

    print("\n4. Select H3C...")
    page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        for (const opt of opts) {
            if (opt.textContent.includes('H3C')) {
                opt.querySelector('input').click();
                break;
            }
        }
    }''')
    page.wait_for_timeout(2000)

    after_h3c = page.evaluate('''() => {
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root;
        let component = null;
        const walk = (v) => {
            if (v?.$options?.name === 'GeneralModel') component = v;
            (v?.$children || []).forEach(walk);
        };
        walk(vm);
        return {
            filterValues: component?.filter?.values,
            filterValue: component?.filter?.value,
            enumDropdownVisible: component?.enumDropdownVisible
        };
    }''')
    print(f"   After H3C: {after_h3c}")

    print("\n5. Click input to reopen dropdown...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)

    # Check if dropdown is open
    dropdown_state = page.evaluate('''() => {
        const dropdown = document.querySelector('.enum-dropdown');
        return {
            exists: !!dropdown,
            display: dropdown ? window.getComputedStyle(dropdown).display : 'none'
        };
    }''')
    print(f"   Dropdown state: {dropdown_state}")

    print("\n6. Select Cisco...")
    page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option');
        for (const opt of opts) {
            if (opt.textContent.includes('Cisco')) {
                const input = opt.querySelector('input');
                console.log('Before click - input checked:', input.checked);
                input.click();
                console.log('After click - input checked:', input.checked);
                break;
            }
        }
    }''')
    page.wait_for_timeout(2000)

    after_cisco = page.evaluate('''() => {
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root;
        let component = null;
        const walk = (v) => {
            if (v?.$options?.name === 'GeneralModel') component = v;
            (v?.$children || []).forEach(walk);
        };
        walk(vm);
        return {
            filterValues: component?.filter?.values,
            filterValue: component?.filter?.value,
            enumDropdownVisible: component?.enumDropdownVisible
        };
    }''')
    print(f"   After Cisco: {after_cisco}")

    # Check checkboxes state
    checkbox_state = page.evaluate('''() => {
        const opts = document.querySelectorAll('.enum-dropdown .enum-option input');
        return Array.from(opts).map(i => ({
            value: i.value,
            checked: i.checked
        }));
    }''')
    print(f"   Checkbox state: {checkbox_state}")

    print("\n7. Console logs:")
    for log in console_logs:
        if 'handleEnum' in log or 'filter.values' in log:
            print(f"   {log}")

    page.screenshot(path='/tmp/debug2.png', full_page=True)

    print("\nTest completed!")
    browser.close()
