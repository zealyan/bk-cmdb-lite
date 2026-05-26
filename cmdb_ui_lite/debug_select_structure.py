from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Click field selector to open dropdown...")
    field_select = page.locator('.filter-selector .bk-select')
    field_select.click()
    page.wait_for_timeout(1500)

    # Get complete body structure to find where bk-options rendered
    full_structure = page.evaluate('''() => {
        // Find all bk-select elements in the page
        const allSelects = document.querySelectorAll('.bk-select');
        const result = [];

        allSelects.forEach((select, i) => {
            // Check if this is the field selector
            const isFieldSelector = select.closest('.filter-selector') !== null;

            if (isFieldSelector) {
                result.push({
                    index: i,
                    isFieldSelector: true,
                    outerHTML: select.outerHTML,
                    innerHTML: select.innerHTML,
                    parentOuterHTML: select.parentElement?.outerHTML?.substring(0, 500) || 'no parent'
                });
            }
        });

        // Also search for bk-options anywhere in the document
        const allOptions = document.querySelectorAll('.bk-option, .bk-options, .bk-option-list');
        const optionsResult = [];
        allOptions.forEach((opt, i) => {
            optionsResult.push({
                index: i,
                tag: opt.tagName,
                class: opt.className,
                text: opt.textContent.trim().substring(0, 100),
                parent: opt.parentElement?.className || ''
            });
        });

        // Search for tooltip content
        const tooltips = document.querySelectorAll('.bk-tooltip, .tippy-box, .tippy-content');
        const tooltipResult = [];
        tooltips.forEach((tip, i) => {
            if (i < 10) {
                tooltipResult.push({
                    index: i,
                    class: tip.className,
                    html: tip.innerHTML?.substring(0, 200) || ''
                });
            }
        });

        return {
            fieldSelectors: result,
            allOptions: optionsResult,
            tooltips: tooltipResult
        };
    }''')

    print(f"   Structure: {full_structure}")

    page.screenshot(path='/tmp/d_dropdown_open.png', full_page=True)

    print("\nTest completed!")
    browser.close()
