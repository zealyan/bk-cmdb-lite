from playwright.sync_api import sync_playwright
import time

def test_debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        # Monitor all console messages
        def log_console(msg):
            print(f"[Console {msg.type}] {msg.text[:200]}")
        page.on('console', log_console)

        print("正在导航到首页...")
        response = page.goto('http://localhost:8080', timeout=60000)
        print(f"页面响应状态: {response.status}")

        print("等待页面加载...")
        page.wait_for_load_state('domcontentloaded', timeout=60000)

        time.sleep(5)

        # Save initial screenshot
        page.screenshot(path='/tmp/test_initial.png', full_page=True)

        # Get page content
        print("\n页面内容:")
        content = page.content()
        print(f"总长度: {len(content)} 字符")

        # Look for app content
        app = page.locator('#app')
        if app.count() > 0:
            inner = app.inner_html()
            print(f"#app 内容长度: {len(inner)} 字符")
            print(f"#app 内容预览: {inner[:500]}...")

        # Check for router-view
        router_view = page.locator('router-view, [class*="router"]')
        print(f"Router view elements: {router_view.count()}")

        # Check for any visible text
        body = page.locator('body')
        body_text = body.inner_text()
        print(f"Body text: {body_text[:500] if body_text else 'Empty'}")

        # Try navigating directly to the models route
        print("\n\n直接导航到 /#/models/bk_switch...")
        page.goto('http://localhost:8080/#/models/bk_switch', timeout=60000)
        time.sleep(5)

        page.screenshot(path='/tmp/test_models.png', full_page=True)

        content2 = page.content()
        print(f"页面内容长度: {len(content2)}")

        app2 = page.locator('#app')
        if app2.count() > 0:
            inner2 = app2.inner_html()
            print(f"#app 内容长度: {len(inner2)}")
            print(f"#app 内容预览: {inner2[:500]}...")

        browser.close()

if __name__ == '__main__':
    test_debug()
