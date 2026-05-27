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

    print("3. Check bk-select component registration...")
    component_check = page.evaluate('''() => {
        // Check if bk-select is registered globally
        const Vue = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue;
        if (!Vue) return 'Vue devtools not available';

        // Check if component is registered
        const components = Vue.options?.components;
        const bkSelect = components?.['bk-select'] || components?.['BkSelect'];

        // Check if bkmagic is loaded
        const bkMagicVue = window.bkMagicVue;
        const bkMagicComponents = bkMagicVue?.options?.components;

        // Try to get component definition
        let componentDef = null;
        if (Vue.component) {
            componentDef = Vue.component('bk-select');
        }

        return {
            hasComponents: !!components,
            hasBkSelect: !!bkSelect,
            hasBkMagic: !!bkMagicVue,
            bkMagicComponentsCount: bkMagicComponents ? Object.keys(bkMagicComponents).length : 0,
            componentDef: componentDef ? 'found' : 'not found'
        };
    }''')
    print(f"   Component check: {component_check}")

    # Check for any errors or warnings related to bk-select
    print("4. Console logs related to bk-select or options...")
    for log in console_logs:
        if 'bk-select' in log.lower() or 'options' in log.lower() or 'option' in log.lower():
            print(f"   {log}")

    page.screenshot(path='/tmp/component_check.png', full_page=True)

    print("Test completed!")
    browser.close()
