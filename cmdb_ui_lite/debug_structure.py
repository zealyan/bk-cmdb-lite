from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("1. Navigate to switch page...")
    page.goto('http://localhost:8080/#/instance/bk_switch')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    print("2. Get complete page structure...")
    # Get all HTML
    html = page.content()
    print(f"   Page HTML length: {len(html)}")

    # Get the filter section HTML
    filter_html = page.evaluate('''() => {
        const filterSection = document.querySelector('.options-filter');
        return filterSection ? filterSection.outerHTML : 'NOT FOUND';
    }''')
    print(f"\n3. Filter section HTML:\n{filter_html[:3000]}")

    # Get all bk-select elements info
    selects_info = page.evaluate('''() => {
        const selects = document.querySelectorAll('.bk-select');
        return Array.from(selects).map((s, i) => ({
            index: i,
            class: s.className,
            id: s.id,
            text: s.textContent.trim().substring(0, 100),
            parent: s.parentElement?.className || 'unknown'
        }));
    }''')
    print(f"\n4. All bk-select elements ({len(selects_info)}):")
    for s in selects_info:
        print(f"   {s}")

    # Get search input related elements
    search_info = page.evaluate('''() => {
        const filterValue = document.querySelector('.filter-value');
        if (!filterValue) return 'filter-value not found';

        const inputs = filterValue.querySelectorAll('input');
        const bkSelects = filterValue.querySelectorAll('.bk-select');
        const divs = filterValue.querySelectorAll('.search-input-wrapper > *');

        return {
            inputs: Array.from(inputs).map(i => ({ type: i.type, placeholder: i.placeholder, class: i.className })),
            bkSelects: bkSelects.length,
            wrapperChildren: divs.length,
            wrapperHTML: filterValue.querySelector('.search-input-wrapper')?.outerHTML || 'no wrapper'
        };
    }''')
    print(f"\n5. Filter value section: {search_info}")

    # Screenshot
    page.screenshot(path='/tmp/structure.png', full_page=True)

    print("\nTest completed!")
    browser.close()
