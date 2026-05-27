from playwright.sync_api import sync_playwright
import time

def test_advanced_filter_style():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("正在访问页面...")
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        print("打开高级筛选...")
        advanced_filter_btn = page.locator('text=高级筛选')
        advanced_filter_btn.click()
        time.sleep(1)
        
        print("点击添加条件...")
        add_condition_btn = page.locator('text=添加条件')
        add_condition_btn.click()
        time.sleep(1)
        
        print("选择属性（选择第一个选项）...")
        # 打开属性选择器
        property_select = page.locator('.condition-picker-trigger').first
        property_select.click()
        time.sleep(1)
        
        # 选择一个枚举类型的属性（如 操作系统）
        # 先选择第一个选项
        first_option = page.locator('.bk-option').first
        first_option.click()
        time.sleep(1)
        
        print("选择值...")
        # 现在筛选项应该已经添加，选择值
        value_select = page.locator('.g-expand .bk-select').first
        value_select.click()
        time.sleep(1)
        
        # 选择几个选项
        options = page.locator('.bk-select-option').all()
        if len(options) >= 2:
            options[0].click()
            time.sleep(0.5)
            options[1].click()
            time.sleep(0.5)
        
        print("截图查看样式...")
        page.screenshot(path='/tmp/advanced_filter_style_test.png', full_page=True)
        print("截图已保存到 /tmp/advanced_filter_style_test.png")
        
        # 检查关键样式
        print("\n检查样式：")
        filter_item = page.locator('.filter-item').first
        bounding_box = filter_item.bounding_box()
        print(f"筛选项位置和尺寸: {bounding_box}")
        
        print("\n检查标签容器...")
        tag_container = page.locator('.bk-select-tag-container').first
        if tag_container.count() > 0:
            tag_bbox = tag_container.bounding_box()
            print(f"标签容器位置和尺寸: {tag_bbox}")
        
        print("\n检查删除按钮位置...")
        remove_btn = page.locator('.filter-item .item-remove').first
        if remove_btn.count() > 0:
            remove_bbox = remove_btn.bounding_box()
            print(f"删除按钮位置和尺寸: {remove_bbox}")
        
        print("\n测试完成！")
        time.sleep(3)
        browser.close()

if __name__ == '__main__':
    test_advanced_filter_style()
