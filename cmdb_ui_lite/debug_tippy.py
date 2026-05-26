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

    print("\n3. Open enum dropdown...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')
    page.wait_for_timeout(2000)

    # Search EVERYTHING for options
    print("\n4. Search entire document for options...")
    everything = page.evaluate('''() => {
        const result = {
            bkOptionCount: document.querySelectorAll('.bk-option').length,
            bkOptionsCount: document.querySelectorAll('.bk-options').length,
            tippyCount: document.querySelectorAll('.tippy').length,
            popupCount: document.querySelectorAll('.bk-popover, .bk-dropdown, .bk-select-dropdown').length,
            bodyChildren: document.body.children.length,
            allPopups: []
        };

        // Search all elements with specific classes
        const searchTerms = ['option', 'dropdown', 'popup', 'select', 'menu', 'list'];
        for (const term of searchTerms) {
            const found = document.querySelectorAll(`[class*="${term}"]`);
            if (found.length > 0) {
                result[`${term}_count`] = found.length;
            }
        }

        // Get all tippy popups
        const tippyPopups = document.querySelectorAll('[id*="tippy"], .tippy-box, .tippy-content');
        result.tippyDetails = Array.from(tippyPopups).slice(0, 5).map(el => ({
            id: el.id,
            class: el.className,
            html: el.innerHTML?.substring(0, 200) || ''
        }));

        // Check for shadow DOM or portals
        result.hasShadowRoot = !!document.querySelector('[_shadow_]') ||
            Array.from(document.querySelectorAll('*')).some(el => el.shadowRoot);

        return result;
    }''')
    print(f"   Everything: {everything}")

    # Get tippy content if it exists
    tippy_content = page.evaluate('''() => {
        const tippyBox = document.querySelector('.tippy-box');
        const tippyContent = document.querySelector('.tippy-content, .tippy-box .tippy-content');

        if (tippyBox || tippyContent) {
            const content = tippyContent || tippyBox;
            return {
                exists: true,
                html: content?.innerHTML?.substring(0, 1000) || 'empty'
            };
        }
        return { exists: false };
    }''')
    print(f"   Tippy content: {tippy_content}")

    # Try clicking the enum select and immediately check for new elements
    print("\n5. Click and immediately search...")
    page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const select = filterValue?.querySelector('.bk-select');
        if (select) select.click();
    }''')

    # Check every 200ms for 2 seconds
    for i in range(10):
        page.wait_for_timeout(200)

        found = page.evaluate('''() => {
            const opts = document.querySelectorAll('.bk-option');
            const optsWrapper = document.querySelectorAll('.bk-options');
            const tippy = document.querySelectorAll('.tippy-box');

            return {
                bkOption: opts.length,
                bkOptionsWrapper: optsWrapper.length,
                tippy: tippy.length,
                // Get any element containing text like Cisco, H3C, etc.
                hasVendorOptions: Array.from(opts).some(o =>
                    o.textContent.includes('Cisco') ||
                    o.textContent.includes('H3C') ||
                    o.textContent.includes('Huawei')
                )
            };
        }''')

        print(f"   Check {i+1}: {found}")
        if found['bkOption'] > 0 or found['hasVendorOptions']:
            print(f"   Found options!")
            break

    page.screenshot(path='/tmp/enum_tippy.png', full_page=True)

    print("\nTest completed!")
    browser.close()
