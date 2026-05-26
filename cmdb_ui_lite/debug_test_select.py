from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

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

    print("3. Inject test code to create a test select...")

    # Inject a simple test select with known working options
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');

        // Create a test div
        const testDiv = document.createElement('div');
        testDiv.id = 'test-select-container';
        testDiv.innerHTML = '<bk-select id="test-select" placeholder="Test" list="[{id: \\'opt1\\', name: \\'Option 1\\'}, {id: \\'opt2\\', name: \\'Option 2\\'}]"></bk-select>';
        filterValue.appendChild(testDiv);
    }''')
    page.wait_for_timeout(2000)

    # Click the test select
    page.evaluate('''() => {
        const testSelect = document.querySelector('#test-select-container .bk-select');
        if (testSelect) testSelect.click();
    }''')
    page.wait_for_timeout(2000)

    # Check if test select has options
    test_result = page.evaluate('''() => {
        const container = document.querySelector('#test-select-container');
        const select = container.querySelector('.bk-select');
        const vue = select?.__vue__;
        const optionListRef = vue?.$refs?.optionList;

        return {
            hasSelect: !!select,
            listProp: vue?.$props?.list,
            optionListHTML: optionListRef?.innerHTML,
            bkOptionsInPage: document.querySelectorAll('.bk-option').length
        };
    }''')
    print(f"   Test result: {test_result}")

    # Remove test container
    page.evaluate('''() => {
        const testDiv = document.querySelector('#test-select-container');
        if (testDiv) testDiv.remove();
    }''')

    print("Test completed!")
    browser.close()
