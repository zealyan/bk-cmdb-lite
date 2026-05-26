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

    print("3. Debug enumOptions via console...")

    # Inject debug code to log enumOptions
    page.evaluate('''() => {
        // Find the GeneralModel component
        const findVue = (el) => {
            let current = el;
            while (current) {
                if (current.__vue__) return current.__vue__;
                current = current.parentElement;
            }
            return null;
        };

        // Try to find it
        const root = document.querySelector('#app') || document.body;
        const vm = findVue(root);

        if (vm) {
            console.log('Vue instance found:', vm.$options.name);
            if (vm.$options.name === 'GeneralModel') {
                console.log('allProperties:', JSON.stringify(vm.allProperties));
                console.log('filterProperty:', JSON.stringify(vm.filterProperty));
                console.log('isEnumField:', vm.isEnumField);
                console.log('enumOptions:', JSON.stringify(vm.enumOptions));
            }
        } else {
            // Search all elements with __vue__
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                if (el.__vue__ && el.__vue__.$options?.name === 'GeneralModel') {
                    const component = el.__vue__;
                    console.log('Found GeneralModel!');
                    console.log('allProperties count:', component.allProperties?.length);
                    console.log('filter field:', component.filter?.field);
                    console.log('filterProperty:', JSON.stringify(component.filterProperty));
                    console.log('isEnumField:', component.isEnumField);
                    console.log('enumOptions:', JSON.stringify(component.enumOptions));

                    // Find vendor property specifically
                    const vendorProp = component.allProperties?.find(p => p.bk_property_id === 'vendor');
                    console.log('Vendor property:', JSON.stringify(vendorProp));
                    break;
                }
            }
        }
    }''')

    page.wait_for_timeout(1000)

    print("\n4. Console logs from debug:")
    for log in console_logs:
        if 'allProperties' in log or 'enumOptions' in log or 'filterProperty' in log or 'Vendor' in log or 'vendor' in log:
            print(f"   {log}")

    # Also check what's in allProperties
    print("\n5. Check allProperties structure...")
    all_props = page.evaluate('''() => {
        // Try different methods to find Vue component
        try {
            // Method: Find by Vue component name in the DOM
            const app = document.querySelector('#app, .app');
            if (app && app.__vue__) {
                return { method: 'app.__vue__', name: app.__vue__.$options?.name };
            }
        } catch(e) {}

        // Method: Try window.Vue
        if (window.Vue) {
            try {
                const instances = [];
                // Vue 3 style
                if (window.Vue._instance) {
                    const walk = (vm) => {
                        if (vm.$options?.name === 'GeneralModel') instances.push(vm);
                        (vm.$children || []).forEach(walk);
                    };
                    walk(window.Vue._instance);
                    if (instances.length > 0) {
                        return {
                            method: 'Vue._instance',
                            props: instances[0].allProperties?.map(p => ({
                                id: p.bk_property_id,
                                type: p.bk_property_type,
                                option: p.option,
                                bk_property_option: p.bk_property_option
                            }))
                        };
                    }
                }
            } catch(e) {}
        }

        return { error: 'Could not find Vue instance' };
    }''')
    print(f"   {all_props}")

    print("\nTest completed!")
    browser.close()
