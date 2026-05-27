from playwright.sync_api import sync_playwright
import time

def inspect_advanced_filter():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("正在访问页面...")
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        print("当前页面内容已加载")
        page.screenshot(path='/tmp/page_initial.png')
        
        print("查找高级筛选按钮...")
        advanced_filter = page.locator('button:has-text("高级筛选")')
        if advanced_filter.count() > 0:
            print("找到高级筛选按钮")
            advanced_filter.click()
            time.sleep(2)
            page.screenshot(path='/tmp/advanced_filter_opened.png')
            print("高级筛选已打开，截图已保存到 /tmp/advanced_filter_opened.png")
        else:
            print("未找到高级筛选按钮")
        
        print("\n页面检查完成！")
        print("请在打开的浏览器中手动测试高级筛选功能")
        print("按 Ctrl+C 或关闭浏览器来停止脚本")
        
        # 保持浏览器打开一段时间
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
            
        browser.close()

if __name__ == '__main__':
    inspect_advanced_filter()
