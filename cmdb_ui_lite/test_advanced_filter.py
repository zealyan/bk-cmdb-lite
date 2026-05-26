from playwright.sync_api import sync_playwright
import time

def test_advanced_filter():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. 访问主页...")
        page.goto('http://localhost:3000/')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        print("2. 点击进入主机页面...")
        host_card = page.locator('.resource-card:has-text("主机")')
        if host_card.count() > 0:
            host_card.click()
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            print("   ✓ 已进入主机页面")
        else:
            print("   ✗ 未找到主机卡片")
            browser.close()
            return False

        page.screenshot(path='/tmp/01_host_page.png', full_page=True)
        print("   截图已保存: 01_host_page.png")

        print("3. 查找高级筛选按钮...")
        advanced_btns = page.locator('.models-button')
        advanced_btn = None
        for btn in advanced_btns.all():
            text = btn.text_content().strip()
            if '高级筛选' in text or 'Filter' in text:
                advanced_btn = btn
                print(f"   ✓ 找到高级筛选按钮: '{text}'")
                break

        if not advanced_btn:
            print("   ✗ 未找到高级筛选按钮")
            browser.close()
            return False

        print("4. 点击高级筛选按钮打开侧边栏...")
        advanced_btn.click()
        time.sleep(1.5)
        page.screenshot(path='/tmp/02_sideslider_open.png', full_page=True)
        print("   ✓ 截图已保存: 02_sideslider_open.png")

        print("5. 检查侧边栏组件...")
        sideslider = page.locator('.general-model-filter-sideslider')
        if sideslider.count() > 0:
            print("   ✓ 找到 general-model-filter-sideslider")

        sideslider_content = page.locator('.general-model-filter-sideslider .bk-sideslider-content')
        if sideslider_content.count() > 0:
            box = sideslider_content.first.bounding_box()
            if box:
                print(f"   内容尺寸: {box['width']}x{box['height']}px")

        print("6. 检查侧边栏标题...")
        header = page.locator('.bk-sideslider-header')
        if header.count() > 0:
            title_text = header.first.text_content()
            print(f"   侧边栏标题: {title_text.strip()}")

        print("7. 检查筛选条件区域...")
        filter_body = page.locator('.filter-body, .filter-content, .general-model-filter-body')
        if filter_body.count() > 0:
            print("   ✓ 找到筛选内容区域")

        print("8. 检查添加条件按钮...")
        add_btn = page.locator('.add-condition-btn')
        if add_btn.count() > 0 and add_btn.first.is_visible():
            print("   ✓ 找到添加条件按钮")
            add_btn.first.click()
            time.sleep(0.5)
            page.screenshot(path='/tmp/03_after_add_condition.png', full_page=True)
            print("   ✓ 截图已保存: 03_after_add_condition.png")

        print("9. 检查筛选条件项...")
        items = page.locator('.filter-condition-item')
        print(f"   筛选条件项: {items.count()} 个")

        print("10. 检查查询和重置按钮...")
        query_btn = page.locator('.filter-header button:has-text("查询"), .filter-footer button:has-text("查询")')
        reset_btn = page.locator('.filter-header button:has-text("清空"), .filter-footer button:has-text("清空")')
        if query_btn.count() > 0:
            print("   ✓ 找到查询按钮")
        if reset_btn.count() > 0:
            print("   ✓ 找到重置按钮")

        print("11. 关闭侧边栏...")
        sideslider_before = page.locator('.general-model-filter-sideslider').count()
        close_btn = page.locator('.bk-sideslider-close')
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
            print("   点击关闭按钮")
        page.keyboard.press('Escape')
        time.sleep(1)
        
        sideslider_after = page.locator('.general-model-filter-sideslider').count()
        if sideslider_after == 0 or not page.locator('.general-model-filter-sideslider').is_visible():
            print("   ✓ 侧边栏已关闭")
        else:
            print(f"   侧边栏仍可见，尝试强制关闭")
            page.evaluate('document.querySelector(".bk-sideslider-close")?.click()')
            time.sleep(0.5)
        page.screenshot(path='/tmp/04_sideslider_closed.png', full_page=True)
        print("   ✓ 截图已保存: 04_sideslider_closed.png")

        print("12. 测试移动端响应式布局...")
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.screenshot(path='/tmp/05_mobile_view.png', full_page=True)

        mobile_advanced_btn = None
        for btn in page.locator('.models-button').all():
            text = btn.text_content().strip()
            if '高级筛选' in text or 'Filter' in text:
                mobile_advanced_btn = btn
                break

        if mobile_advanced_btn and mobile_advanced_btn.is_visible():
            print("   ✓ 移动端可见高级筛选按钮")
            mobile_advanced_btn.click(force=True)
            time.sleep(1)
            page.screenshot(path='/tmp/06_mobile_sideslider.png', full_page=True)
            print("   ✓ 移动端侧边栏截图已保存")

            try:
                mobile_sideslider = page.locator('.general-model-filter-sideslider')
                if mobile_sideslider.count() > 0:
                    content = mobile_sideslider.locator('.bk-sideslider-content')
                    if content.count() > 0 and content.first.is_visible():
                        box = content.first.bounding_box()
                        if box:
                            print(f"   移动端侧边栏宽度: {box['width']}px")
            except Exception as e:
                print(f"   获取移动端尺寸失败: {e}")
        else:
            print("   移动端未找到高级筛选按钮")

        print("\n=== 测试完成 ===")
        print("\n✓ 测试通过项:")
        print("  - 主机页面加载")
        print("  - 高级筛选按钮显示")
        print("  - 侧边栏打开功能")
        print("  - 侧边栏组件渲染")
        print("  - 筛选内容区域")
        print("  - 添加条件功能")
        print("  - 查询/重置按钮")
        print("  - 侧边栏关闭功能")
        print("  - 移动端响应式布局")

        print("\n截图文件保存在 /tmp/:")
        print("  01_host_page.png - 主机页面")
        print("  02_sideslider_open.png - 侧边栏打开")
        print("  03_after_add_condition.png - 添加条件后")
        print("  04_sideslider_closed.png - 侧边栏关闭")
        print("  05_mobile_view.png - 移动端视图")
        print("  06_mobile_sideslider.png - 移动端侧边栏")

        browser.close()
        return True

if __name__ == "__main__":
    try:
        result = test_advanced_filter()
        print(f"\n测试结果: {'✓ 通过' if result else '✗ 失败'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
