from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    # Get allProperties from Vue component
    print("\n2. Get Vue component data...")
    component_data = page.evaluate('''() => {
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root?.$children[0];
        if (!vm) return 'Vue instance not found';

        const instanceList = vm.$children.find(c => c.$options?.name === 'GeneralModel');
        if (!instanceList) return 'GeneralModel not found';

        return {
            allProperties: instanceList.allProperties?.map(p => ({
                bk_property_id: p.bk_property_id,
                bk_property_type: p.bk_property_type,
                option: p.option
            })),
            isEnumField: instanceList.isEnumField,
            isBoolField: instanceList.isBoolField,
            filterField: instanceList.filter?.field
        };
    }''')

    print(f"   Component data: {component_data}")

    # Try to find vendor field specifically
    vendor_info = page.evaluate('''() => {
        const vm = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.Vue?._instance?.root?.$children[0];
        if (!vm) return 'Vue instance not found';

        const instanceList = vm.$children.find(c => c.$options?.name === 'GeneralModel');
        if (!instanceList) return 'GeneralModel not found';

        const vendorProp = instanceList.allProperties?.find(p => p.bk_property_id === 'vendor');
        return vendorProp || 'vendor not found';
    }''')

    print(f"\n3. Vendor property: {vendor_info}")

    # Check API response
    print("\n4. Making direct API call to check attributes...")
    import requests
    try:
        resp = requests.get('http://localhost:8000/api/attributes/bk_switch', timeout=5)
        data = resp.json()
        print(f"   API response keys: {data.keys() if isinstance(data, dict) else type(data)}")

        if isinstance(data, dict) and 'attributes' in data:
            vendor_in_api = next((p for p in data['attributes'] if p.get('bk_property_id') == 'vendor'), None)
            print(f"   Vendor in API: {vendor_in_api}")
        elif isinstance(data, list):
            vendor_in_api = next((p for p in data if p.get('bk_property_id') == 'vendor'), None)
            print(f"   Vendor in API: {vendor_in_api}")
    except Exception as e:
        print(f"   API error: {e}")

    # Print console logs
    print("\n5. Console logs:")
    for log in console_logs:
        print(f"   {log}")

    print("\nTest completed!")
    browser.close()
