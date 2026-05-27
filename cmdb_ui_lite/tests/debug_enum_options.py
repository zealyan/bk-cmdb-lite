from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(4000)

    print("2. Click field selector...")
    page.locator('.filter-selector .bk-select').click()
    page.wait_for_timeout(1000)

    # Get field options
    field_options = page.evaluate('''() => {
        const options = document.querySelectorAll('.bk-options .bk-option');
        return Array.from(options).map((opt, i) => ({
            index: i,
            text: opt.textContent.trim()
        }));
    }''')
    print(f"   Field options: {field_options}")

    # Click 厂商
    for opt in field_options:
        if '厂商' in opt['text']:
            print(f"\n3. Clicking 厂商 (index {opt['index']})...")
            page.evaluate(f'''() => {{
                const options = document.querySelectorAll('.bk-options .bk-option');
                options[{opt['index']}].click();
            }}''')
            break

    page.wait_for_timeout(1500)
    page.screenshot(path='/tmp/d_enum1.png', full_page=True)

    # Check Vue component state using window
    print("\n4. Getting Vue component state...")

    # Find the Vue app root
    vue_state = page.evaluate('''() => {
        // Try to find Vue instance
        const els = document.querySelectorAll('[id^="app"], #app, .app-container');
        for (const el of els) {
            const vueInstance = el.__vue__;
            if (vueInstance) {
                return {
                    found: true,
                    hasAllProperties: !!vueInstance.allProperties,
                    hasFilterField: !!vueInstance.filter,
                    filterField: vueInstance.filter?.field,
                    isEnumField: vueInstance.isEnumField,
                    isBoolField: vueInstance.isBoolField,
                    enumOptions: vueInstance.enumOptions
                };
            }
        }

        // Try finding GeneralModel component
        const generalModel = document.querySelector('.general-model-layout');
        if (generalModel && generalModel.__vue__) {
            return {
                found: true,
                isGeneralModel: true,
                hasAllProperties: !!generalModel.__vue__.allProperties,
                hasFilterField: !!generalModel.__vue__.filter,
                filterField: generalModel.__vue__.filter?.field,
                isEnumField: generalModel.__vue__.isEnumField,
                isBoolField: generalModel.__vue__.isBoolField,
                enumOptions: generalModel.__vue__.enumOptions
            };
        }

        return { found: false };
    }''')

    print(f"   Vue state: {vue_state}")

    # Check filterProperty directly
    print("\n5. Checking filterProperty...")
    filter_prop_info = page.evaluate('''() => {
        // Try to find GeneralModel component through multiple paths
        let generalModelVue = null;

        // Method 1: Find by component name
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root;
        if (vm) {
            const children = vm.$children || [];
            for (const child of children) {
                if (child.$options?.name === 'GeneralModel') {
                    generalModelVue = child;
                    break;
                }
                // Check deeper
                const grandChildren = child.$children || [];
                for (const grandChild of grandChildren) {
                    if (grandChild.$options?.name === 'GeneralModel') {
                        generalModelVue = grandChild;
                        break;
                    }
                }
            }
        }

        if (!generalModelVue) return 'GeneralModel not found via Vue devtools';

        const fp = generalModelVue.filterProperty;
        const eo = generalModelVue.enumOptions;
        const isEnum = generalModelVue.isEnumField;

        return {
            filterProperty: fp ? {
                bk_property_id: fp.bk_property_id,
                bk_property_type: fp.bk_property_type,
                option: fp.option,
                bk_property_option: fp.bk_property_option
            } : null,
            isEnumField: isEnum,
            enumOptions: eo,
            filterField: generalModelVue.filter?.field
        };
    }''')

    print(f"   Filter property info: {filter_prop_info}")

    # Check the actual rendered HTML for enum select
    print("\n6. Checking enum select HTML...")
    enum_html = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        const enumSelect = filterValue?.querySelector('.bk-select');
        if (!enumSelect) return 'enum select not found';

        return {
            outerHTML: enumSelect.outerHTML,
            bkOptionCount: enumSelect.querySelectorAll('.bk-option').length
        };
    }''')
    print(f"   Enum select HTML: {enum_html}")

    # Get console logs for any errors
    print("\n7. Console logs (errors):")
    for log in console_logs:
        if 'error' in log.lower():
            print(f"   {log}")

    print("\nTest completed!")
    browser.close()
