#!/usr/bin/env python3
"""测试移动端表单适配"""
import os
import sys
sys.path.insert(0, '/data/user/skills/webapp-testing')

from playwright.sync_api import sync_playwright

def test_mobile_form():
    with sync_playwright() as p:
        print("[TEST] 启动移动端浏览器 (375x667)...")
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            viewport={'width': 375, 'height': 667},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        
        page = context.new_page()
        
        url = 'http://localhost:8081/#/instance/bk_switch'
        print(f"[TEST] 导航到实例列表页: {url}")
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        print("[TEST] 截图初始状态...")
        page.screenshot(path='/tmp/mobile_form_1_initial.png', full_page=True)
        
        # 点击新建按钮
        print("[TEST] 点击新建按钮...")
        page.locator('button:has-text("新建")').click()
        page.wait_for_timeout(1500)
        
        print("[TEST] 截图新建弹窗...")
        page.screenshot(path='/tmp/mobile_form_2_dialog.png', full_page=True)
        
        # 检查 sideslider 状态
        slider_state = page.evaluate('''() => {
            const slider = document.querySelector('.bk-sideslider');
            if (!slider) return { found: false };
            
            const main = slider.querySelector('.bk-sideslider-main');
            const style = window.getComputedStyle(main || slider);
            
            return {
                found: true,
                className: slider.className,
                width: main ? main.style.width : 'N/A',
                fullscreen: slider.classList.contains('fullscreen')
            };
        }''')
        print(f"[TEST] Sideslider 状态: {slider_state}")
        
        # 检查表单布局
        form_state = page.evaluate('''() => {
            const form = document.querySelector('.cmdb-form-layout');
            const propertyList = document.querySelector('.property-list');
            const propertyItems = document.querySelectorAll('.property-item');
            const options = document.querySelector('.form-options');
            const buttons = document.querySelectorAll('.form-options .bk-button');
            
            let listStyle = null;
            let itemStyles = [];
            
            if (propertyList) {
                const style = window.getComputedStyle(propertyList);
                listStyle = {
                    flexDirection: style.flexDirection,
                    gap: style.gap
                };
            }
            
            if (propertyItems.length > 0) {
                const style = window.getComputedStyle(propertyItems[0]);
                itemStyles = [{
                    width: style.width,
                    flexBasis: style.flexBasis
                }];
            }
            
            let optionsStyle = null;
            if (options) {
                const style = window.getComputedStyle(options);
                optionsStyle = {
                    position: style.position,
                    padding: style.padding
                };
            }
            
            return {
                formFound: !!form,
                groupCount: document.querySelectorAll('.property-group').length,
                propertyCount: propertyItems.length,
                listStyle: listStyle,
                itemStyles: itemStyles,
                optionsStyle: optionsStyle,
                buttonCount: buttons.length,
                buttonTexts: Array.from(buttons).map(b => b.innerText)
            };
        }''')
        
        print(f"[TEST] 表单状态:")
        print(f"  - 表单组件: {'✓' if form_state['formFound'] else '✗'}")
        print(f"  - 属性分组: {form_state['groupCount']} 个")
        print(f"  - 属性字段: {form_state['propertyCount']} 个")
        print(f"  - 列表布局: {form_state['listStyle']}")
        print(f"  - 字段样式: {form_state['itemStyles']}")
        print(f"  - 操作按钮: {form_state['optionsStyle']}")
        print(f"  - 按钮数量: {form_state['buttonCount']}")
        print(f"  - 按钮文本: {form_state['buttonTexts']}")
        
        # 打印控制台错误
        print("\n[TEST] 完成!")
        
        browser.close()
        
        print("\n" + "="*50)
        print("截图已保存:")
        print("  - /tmp/mobile_form_1_initial.png")
        print("  - /tmp/mobile_form_2_dialog.png")
        print("="*50)

if __name__ == '__main__':
    test_mobile_form()
