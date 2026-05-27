from playwright.sync_api import sync_playwright
import time

def test_enum_dropdown():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        console_logs = []
        def log_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
            if 'error' in msg.type.lower() or 'ERROR' in msg.text:
                print(f"[Console ERROR] {msg.text[:200]}")
        page.on('console', log_console)

        # Correct route: /instance/:objId
        print("正在导航到模型实例列表页...")
        try:
            response = page.goto('http://localhost:8080/#/instance/bk_switch', timeout=60000)
            print(f"页面响应状态: {response.status if response else 'No response'}")
        except Exception as e:
            print(f"导航错误: {e}")

        print("等待网络空闲...")
        try:
            page.wait_for_load_state('networkidle', timeout=60000)
            print("网络已空闲")
        except Exception as e:
            print(f"等待网络空闲超时: {e}")

        time.sleep(5)

        print("保存初始截图...")
        page.screenshot(path='/tmp/test_initial.png', full_page=True)

        print("查找页面元素...")
        selectors_to_try = [
            '.bk-table',
            '.models-table',
            '.general-model-layout',
            'table',
            '.filter-selector',
            '.options-filter'
        ]

        for selector in selectors_to_try:
            try:
                count = page.locator(selector).count()
                print(f"  找到 {count} 个 '{selector}' 元素")
            except Exception as e:
                print(f"  '{selector}' 查询失败: {e}")

        try:
            print("等待 .models-table 元素...")
            page.wait_for_selector('.models-table', timeout=15000)
            print("找到 models-table!")
        except Exception as e:
            print(f"等待 models-table 超时: {e}")

        page.screenshot(path='/tmp/test_after_wait.png', full_page=True)
        print("已保存截图: /tmp/test_after_wait.png")

        # Test field selector dropdown
        print("\n=== 测试字段选择器 ===")
        try:
            field_dropdown = page.locator('.filter-selector .bk-select').first
            if field_dropdown.is_visible(timeout=5000):
                print("找到字段选择器，点击...")
                field_dropdown.click()
                time.sleep(1)
                page.screenshot(path='/tmp/test_field_dropdown.png', full_page=True)

                options = page.locator('.bk-option').all()
                print(f"找到 {len(options)} 个字段选项")
                for opt in options[:15]:
                    try:
                        text = opt.inner_text()
                        if text:
                            print(f"  - {text}")
                    except:
                        pass

                # Click first enum-like option
                enum_opt = None
                for opt in options:
                    try:
                        text = opt.inner_text().lower()
                        if 'enum' in text or '类型' in text or 'category' in text:
                            enum_opt = opt
                            print(f"\n发现枚举字段: {opt.inner_text()}")
                            break
                    except:
                        pass

                if enum_opt:
                    enum_opt.click()
                    time.sleep(1)
                    page.screenshot(path='/tmp/test_enum_selected.png', full_page=True)

                page.keyboard.press('Escape')
                time.sleep(0.5)
            else:
                print("字段选择器不可见")
        except Exception as e:
            print(f"字段选择器测试失败: {e}")

        # Test search value dropdown (enum/bool select)
        print("\n=== 测试搜索值下拉框 ===")
        try:
            search_value = page.locator('.filter-value').first
            if search_value.is_visible(timeout=5000):
                print("找到搜索值区域")
                enum_select = search_value.locator('.bk-select').first
                if enum_select.is_visible(timeout=5000):
                    print("检测到枚举下拉框，点击...")
                    enum_select.click()
                    time.sleep(1)
                    page.screenshot(path='/tmp/test_enum_options.png', full_page=True)

                    enum_opts = page.locator('.bk-option').all()
                    print(f"找到 {len(enum_opts)} 个枚举选项")
                    for opt in enum_opts[:10]:
                        try:
                            text = opt.inner_text()
                            if text:
                                print(f"  - {text}")
                        except:
                            pass

                    if enum_opts:
                        enum_opts[0].click()
                        time.sleep(0.5)
                        page.screenshot(path='/tmp/test_enum_value_selected.png', full_page=True)
                    page.keyboard.press('Escape')
                else:
                    print("没有枚举下拉框（选择了非枚举字段）")
            else:
                print("搜索值区域不可见")
        except Exception as e:
            print(f"枚举下拉框测试失败: {e}")

        # Test advanced filter
        print("\n=== 测试高级筛选 ===")
        try:
            advanced_btn = page.locator('button:has-text("高级筛选")').first
            if advanced_btn.is_visible(timeout=5000):
                print("点击高级筛选按钮...")
                advanced_btn.click()
                time.sleep(2)
                page.screenshot(path='/tmp/test_advanced_filter.png', full_page=True)

                selects = page.locator('.filter-item .bk-select').all()
                print(f"找到 {len(selects)} 个下拉框")
                if len(selects) >= 2:
                    print("点击值选择下拉框...")
                    selects[1].click()
                    time.sleep(1)
                    page.screenshot(path='/tmp/test_advanced_enum.png', full_page=True)

                    adv_opts = page.locator('.bk-option').all()
                    print(f"高级筛选找到 {len(adv_opts)} 个选项")
                    for opt in adv_opts[:10]:
                        try:
                            text = opt.inner_text()
                            if text:
                                print(f"  - {text}")
                        except:
                            pass

                # Close panel
                page.locator('.general-model-filter-sideslider .bk-sideslider-close').click()
                time.sleep(0.5)
            else:
                print("高级筛选按钮不可见")
        except Exception as e:
            print(f"高级筛选测试失败: {e}")

        page.screenshot(path='/tmp/test_final.png', full_page=True)

        # Summary
        print("\n=== 测试完成 ===")
        errors = [log for log in console_logs if 'error' in log.lower() and 'WebSocket' not in log]
        if errors:
            print(f"\n发现 {len(errors)} 个非 WebSocket 控制台错误:")
            for err in errors[:5]:
                print(f"  {err[:200]}")
        else:
            print("没有发现 JavaScript 错误")

        print("\n截图已保存到 /tmp 目录:")
        print("  - test_initial.png: 初始页面")
        print("  - test_field_dropdown.png: 字段选择下拉")
        print("  - test_enum_selected.png: 枚举字段已选择")
        print("  - test_enum_options.png: 枚举选项列表")
        print("  - test_enum_value_selected.png: 枚举值已选择")
        print("  - test_advanced_filter.png: 高级筛选面板")
        print("  - test_advanced_enum.png: 高级筛选枚举下拉")
        print("  - test_final.png: 最终状态")

        browser.close()
        return True

if __name__ == '__main__':
    test_enum_dropdown()
