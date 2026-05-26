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
    page.screenshot(path='/tmp/new1.png', full_page=True)

    print("3. Check for custom enum select...")
    enum_select = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumWrapper = filterValue?.querySelector('.enum-select-wrapper');
        const input = enumWrapper?.querySelector('.enum-multi-input');
        const dropdown = enumWrapper?.querySelector('.enum-dropdown');

        return {
            filterValueExists: !!filterValue,
            enumWrapperExists: !!enumWrapper,
            inputExists: !!input,
            dropdownExists: !!dropdown,
            inputValue: input?.value,
            inputPlaceholder: input?.placeholder,
            dropdownHTML: dropdown?.innerHTML?.substring(0, 500)
        };
    }''')
    print(f"   Enum select: {enum_select}")

    # Click on the input to toggle dropdown
    print("4. Click on enum input to open dropdown...")
    page.evaluate('''() => {
        const input = document.querySelector('.enum-multi-input');
        if (input) input.click();
    }''')
    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/new2.png', full_page=True)

    # Check if dropdown appeared
    dropdown_visible = page.evaluate('''() => {
        const dropdown = document.querySelector('.enum-dropdown');
        return {
            exists: !!dropdown,
            html: dropdown?.innerHTML?.substring(0, 500),
            display: dropdown ? window.getComputedStyle(dropdown).display : 'none'
        };
    }''')
    print(f"   Dropdown visible: {dropdown_visible}")

    # Check for options in dropdown
    options = page.evaluate('''() => {
        const options = document.querySelectorAll('.enum-dropdown .enum-option');
        return Array.from(options).map(o => o.textContent.trim());
    }''')
    print(f"   Options in dropdown: {options}")

    if options:
        print("\n5. Click on first option...")
        page.evaluate('''() => {
            const firstOption = document.querySelector('.enum-dropdown .enum-option');
            if (firstOption) firstOption.click();
        }''')
        page.wait_for_timeout(2000)
        page.screenshot(path='/tmp/new3.png', full_page=True)

        # Check if search was triggered
        search_logs = [log for log in console_logs if 'loadModelData' in log]
        print(f"   Search logs: {search_logs}")

    print("\n6. Console logs (last 10):")
    for log in console_logs[-10:]:
        print(f"   {log}")

    print("\nTest completed!")
    browser.close()
