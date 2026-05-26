from playwright.sync_api import sync_playwright
import time

def test_enum_multi_select():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("1. 导航到交换机实例列表页面...")
        page.goto('http://localhost:8080/#/instance/bk_switch')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        print("2. 截图初始状态...")
        page.screenshot(path='/tmp/01_initial.png', full_page=True)
        
        print("3. 查找并选择'厂商'字段...")
        field_selector = page.locator('.filter-selector .bk-select')
        field_selector.click()
        time.sleep(0.5)
        
        field_option = page.locator('.bk-option:has-text("厂商")')
        field_option.click()
        time.sleep(1)
        
        print("4. 截图选择字段后状态...")
        page.screenshot(path='/tmp/02_field_selected.png', full_page=True)
        
        print("5. 检查下拉箭头图标是否存在...")
        angle_icon = page.locator('.bk-select-angle')
        icon_count = angle_icon.count()
        print(f"   找到 {icon_count} 个下拉箭头图标")
        
        if icon_count > 0:
            icon_classes = angle_icon.first.get_attribute('class')
            print(f"   图标类名: {icon_classes}")
            
            icon_html = angle_icon.first.evaluate('el => el.outerHTML')
            print(f"   图标 HTML: {icon_html}")
        
        print("6. 点击输入框打开下拉菜单...")
        enum_input = page.locator('.enum-multi-input')
        enum_input.click()
        time.sleep(1)
        
        print("7. 截图下拉菜单打开状态...")
        page.screenshot(path='/tmp/03_dropdown_open.png', full_page=True)
        
        print("8. 检查下拉选项...")
        options = page.locator('.bk-select-option')
        option_count = options.count()
        print(f"   找到 {option_count} 个选项")
        
        option_names = []
        for i in range(option_count):
            name = options.nth(i).locator('.bk-select-option-name').inner_text()
            option_names.append(name)
        print(f"   选项列表: {option_names}")
        
        print("9. 选择第一个选项 (H3C)...")
        first_option = page.locator('.bk-select-option:has-text("H3C")')
        first_option.click()
        time.sleep(0.5)
        
        print("10. 截图选择第一个选项后...")
        page.screenshot(path='/tmp/04_first_selected.png', full_page=True)
        
        input_value = enum_input.get_attribute('value')
        print(f"   输入框值: {input_value}")
        
        print("11. 选择第二个选项 (Cisco)...")
        second_option = page.locator('.bk-select-option:has-text("Cisco")')
        second_option.click()
        time.sleep(0.5)
        
        print("12. 截图选择第二个选项后...")
        page.screenshot(path='/tmp/05_second_selected.png', full_page=True)
        
        input_value = enum_input.get_attribute('value')
        print(f"   输入框值: {input_value}")
        
        print("13. 检查选中项的打钩图标...")
        check_icons = page.locator('.bk-select-check')
        check_count = check_icons.count()
        print(f"   找到 {check_count} 个打钩图标")
        
        print("14. 检查搜索框...")
        search_input = page.locator('.bk-select-search-input')
        search_visible = search_input.is_visible()
        print(f"   搜索框可见: {search_visible}")
        
        if search_visible:
            print("15. 测试搜索功能...")
            search_input.fill('Huawei')
            time.sleep(0.5)
            
            filtered_options = page.locator('.bk-select-option:visible')
            filtered_count = filtered_options.count()
            print(f"   过滤后选项数量: {filtered_count}")
            
            page.screenshot(path='/tmp/06_search_filtered.png', full_page=True)
        
        print("\n=== 测试结果 ===")
        print(f"✅ 下拉箭头图标: {'存在' if icon_count > 0 else '不存在'}")
        print(f"✅ 下拉选项数量: {option_count}")
        print(f"✅ 多选功能: {input_value}")
        print(f"✅ 打钩图标数量: {check_count}")
        print(f"✅ 搜索框: {'可用' if search_visible else '不可用'}")
        
        browser.close()
        print("\n测试完成!")

if __name__ == '__main__':
    test_enum_multi_select()
