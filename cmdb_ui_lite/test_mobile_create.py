#!/usr/bin/env python3
"""测试新建实例功能"""
import os
import sys
sys.path.insert(0, '/data/user/skills/webapp-testing')

from playwright.sync_api import sync_playwright

def test_create_instance():
    with sync_playwright() as p:
        print("[TEST] 启动浏览器...")
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            viewport={'width': 375, 'height': 667},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        
        page = context.new_page()
        
        console_logs = []
        page.on('console', lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text
        }))
        
        url = 'http://localhost:8081/#/instance/bk_switch'
        print(f"[TEST] 导航到实例列表页: {url}")
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        print("[TEST] 截图初始状态...")
        page.screenshot(path='/tmp/mobile_initial.png', full_page=True)
        
        print("[TEST] 点击新建按钮...")
        try:
            page.locator('button:has-text("新建")').first.click()
            print("[TEST] 新建按钮点击成功!")
        except Exception as e:
            print(f"[ERROR] 点击失败: {e}")
        
        page.wait_for_timeout(2000)
        
        print("[TEST] 截图点击后状态...")
        page.screenshot(path='/tmp/mobile_after_click.png', full_page=True)
        
        # 检查 sideslider
        sideslider_state = page.evaluate('''() => {
            const slider = document.querySelector('.bk-sideslider');
            if (!slider) return { found: false };
            
            const style = window.getComputedStyle(slider);
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
            
            return {
                found: true,
                display: style.display,
                visibility: style.visibility,
                isVisible: isVisible
            };
        }''')
        
        print(f"\n[TEST] Sideslider 状态: {sideslider_state}")
        
        # 检查 cmdb-form
        form_state = page.evaluate('''() => {
            const form = document.querySelector('.cmdb-form-layout');
            const groups = document.querySelectorAll('.property-group');
            const buttons = document.querySelectorAll('.form-options .bk-button');
            
            return {
                formFound: !!form,
                groupCount: groups.length,
                buttonCount: buttons.length,
                buttons: Array.from(buttons).map(b => b.innerText)
            };
        }''')
        
        print(f"[TEST] Form 状态: {form_state}")
        
        # 打印相关控制台日志
        print("\n[CONSOLE LOGS] (前20条):")
        for log in console_logs[:20]:
            print(f"  [{log['type']}] {log['text'][:150]}")
        
        browser.close()
        
        print("\n" + "="*50)
        print("测试完成! 截图保存在:")
        print("  - /tmp/mobile_initial.png (初始状态)")
        print("  - /tmp/mobile_after_click.png (点击后状态)")
        print("="*50)

if __name__ == '__main__':
    test_create_instance()
