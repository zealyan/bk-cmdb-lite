from playwright.sync_api import sync_playwright
import time

def test_enum_multiselect():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        console_logs = []
        def log_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
        page.on('console', log_console)

        print("正在导航到交换机实例列表...")
        page.goto('http://localhost:8080/#/instance/bk_switch', timeout=60000)
        page.wait_for_load_state('networkidle', timeout=60000)
        time.sleep(5)
        page.screenshot(path='/tmp/test_multi_initial.png')

        try:
            page.wait_for_selector('.models-table', timeout=15000)
            print("数据表已加载")
        except Exception as e:
            print(f"错误: {e}")
            return

        # Select "厂商" field
        print("\n=== 选择枚举字段 ===")
        field_select = page.locator('.filter-selector .bk-select').first
        field_select.click()
        time.sleep(1)
        page.screenshot(path='/tmp/test_field_open.png')

        # Try different selectors for dropdown options
        options = (page.locator('.bk-option-list .bk-option').all() or
                   page.locator('.bk-select-dropdown .bk-option').all() or
                   page.locator('.bk-options .bk-option').all() or
                   page.locator('.bk-select-options .bk-option').all())

        print(f"找到 {len(options)} 个选项")

        for opt in options:
            try:
                text = opt.inner_text()
                if '厂商' in text:
                    opt.click()
                    print(f"已选择: {text}")
                    break
            except:
                pass

        time.sleep(1)
        page.screenshot(path='/tmp/test_field_selected.png')

        # Check for enum multi-select dropdown
        print("\n=== 检查枚举多选下拉框 ===")
        enum_select = page.locator('.filter-value .bk-select').first
        if enum_select.is_visible():
            print("找到枚举下拉框")

            # Get the dropdown trigger area and click
            enum_select.click()
            time.sleep(1)
            page.screenshot(path='/tmp/test_enum_dropdown_open.png')

            # Try different selectors for dropdown
            dropdown_options = []

            # Try various selectors
            selectors = [
                '.bk-dropdown-list .bk-option',
                '.bk-select-dropdown .bk-option',
                '.bk-options .bk-option',
                '.bk-select-options .bk-option',
                '.bk-option-list .bk-option',
                '[class*="dropdown"] .bk-option',
                '[class*="select"] .bk-option',
                '.bk-option'
            ]

            for sel in selectors:
                opts = page.locator(sel).all()
                if opts:
                    dropdown_options = opts
                    print(f"使用选择器 '{sel}' 找到 {len(opts)} 个选项")
                    break

            if not dropdown_options:
                # Try to get any visible option
                dropdown_options = page.locator('.bk-option:visible').all()

            print(f"枚举选项数量: {len(dropdown_options)}")

            for i, opt in enumerate(dropdown_options[:5]):
                try:
                    text = opt.inner_text()
                    print(f"  选项 {i+1}: {text}")
                except:
                    pass

            if dropdown_options:
                # Click first option
                dropdown_options[0].click()
                time.sleep(0.5)

                # Open dropdown again and click second option
                enum_select.click()
                time.sleep(0.5)

                dropdown_options2 = page.locator('.bk-option:visible').all()
                if len(dropdown_options2) > 1:
                    dropdown_options2[1].click()
                    time.sleep(0.5)

                page.screenshot(path='/tmp/test_two_selected.png')

                # Check selected values
                selected_tags = page.locator('.bk-select .bk-tag').all()
                print(f"选中标签数量: {len(selected_tags)}")
                for tag in selected_tags:
                    try:
                        print(f"  标签: {tag.inner_text()}")
                    except:
                        pass

                time.sleep(2)
                page.screenshot(path='/tmp/test_after_search.png')

        # Final check
        print("\n=== 测试完成 ===")
        errors = [log for log in console_logs if 'error' in log.lower() and 'WebSocket' not in log]
        if errors:
            print(f"错误数量: {len(errors)}")
            for err in errors[:3]:
                print(f"  {err[:100]}")
        else:
            print("没有 JavaScript 错误")

        print("\n截图已保存到 /tmp")
        browser.close()
        return True

if __name__ == '__main__':
    test_enum_multiselect()
