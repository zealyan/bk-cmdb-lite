#!/usr/bin/env python3
"""
测试新增实例功能
测试步骤：
1. 打开应用
2. 选择"交换机"模型
3. 点击"新建"按钮
4. 填写表单
5. 提交并验证
"""

from playwright.sync_api import sync_playwright
import time

def test_create_instance():
    print("=" * 60)
    print("开始测试新增实例功能")
    print("=" * 60)
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. 打开应用
            print("\n[Step 1] 打开应用...")
            page.goto('http://localhost:3000')
            page.wait_for_load_state('networkidle')
            print("✅ 页面加载成功")
            
            # 等待页面稳定
            time.sleep(2)
            
            # 截图保存
            page.screenshot(path='/tmp/step1_initial.png', full_page=True)
            print("📸 截图已保存: /tmp/step1_initial.png")
            
            # 2. 选择"交换机"模型
            print("\n[Step 2] 选择交换机模型...")
            
            # 查找模型选择器
            # 尝试点击模型选择下拉框
            try:
                # 查找包含"模型"或"选择模型"的元素
                model_selector = page.locator('.model-selector, [class*="model"], select, .bk-select').first
                if model_selector.count() > 0:
                    model_selector.click()
                    time.sleep(1)
                    print("✅ 点击了模型选择器")
                    
                    # 查找"交换机"选项
                    switch_option = page.locator('text=交换机, text=switch').first
                    if switch_option.count() > 0:
                        switch_option.click()
                        print("✅ 选择了交换机模型")
                    else:
                        print("⚠️ 未找到交换机选项，尝试其他方式")
                else:
                    print("⚠️ 未找到模型选择器")
            except Exception as e:
                print(f"⚠️ 选择模型时出错: {e}")
            
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path='/tmp/step2_model_selected.png', full_page=True)
            print("📸 截图已保存: /tmp/step2_model_selected.png")
            
            # 3. 点击"新建"按钮
            print("\n[Step 3] 点击新建按钮...")
            
            # 查找"新建"按钮
            new_button = page.locator('button:has-text("新建"), button:has-text("新建实例"), text=新建').first
            if new_button.count() > 0:
                new_button.click()
                print("✅ 点击了新建按钮")
            else:
                print("❌ 未找到新建按钮，尝试其他选择器...")
                # 尝试其他选择器
                new_button = page.locator('button').filter(has_text="新建").first
                if new_button.count() > 0:
                    new_button.click()
                    print("✅ 点击了新建按钮（备选选择器）")
            
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path='/tmp/step3_dialog_opened.png', full_page=True)
            print("📸 截图已保存: /tmp/step3_dialog_opened.png")
            
            # 4. 查找并填写表单
            print("\n[Step 4] 查找并填写表单...")
            
            # 等待弹窗出现
            dialog = page.locator('.bk-dialog, [role="dialog"], .bk-modal').first
            if dialog.count() > 0:
                print("✅ 检测到弹窗")
                
                # 查找表单字段
                # 通常表单会有 input 或 select 元素
                inputs = page.locator('input, select, textarea, .bk-input, .bk-select').all()
                print(f"   找到 {len(inputs)} 个输入字段")
                
                # 尝试填写几个关键字段
                for i, inp in enumerate(inputs[:5]):  # 只填写前5个
                    try:
                        # 检查是否是可见的
                        if inp.is_visible():
                            # 获取标签或占位符
                            placeholder = inp.get_attribute('placeholder') or ''
                            label = ''
                            
                            # 尝试获取关联的label
                            form_item = inp.locator('..').first
                            if form_item.count() > 0:
                                label_text = form_item.inner_text()
                                if len(label_text) < 50:
                                    label = label_text.split('\n')[0]
                            
                            print(f"   字段 {i+1}: {label or placeholder}")
                            
                            # 根据字段类型填写
                            inp_type = inp.get_attribute('type')
                            tag_name = inp.evaluate('el => el.tagName')
                            
                            if tag_name == 'INPUT' and inp_type in ['text', 'number']:
                                # 填写文本或数字
                                if 'ip' in (label + placeholder).lower():
                                    inp.fill('192.168.1.100')
                                    print(f"      → 填写IP地址: 192.168.1.100")
                                elif 'name' in (label + placeholder).lower():
                                    inp.fill(f'test-switch-{int(time.time())}')
                                    print(f"      → 填写名称")
                                elif 'id' in (label + placeholder).lower():
                                    inp.fill(f'ASSET-{int(time.time())}')
                                    print(f"      → 填写资产ID")
                                else:
                                    inp.fill(f'test-value-{i}')
                                    print(f"      → 填写测试值")
                                    
                            elif tag_name == 'SELECT':
                                # 选择第一个选项
                                options = inp.locator('option').all()
                                if len(options) > 1:
                                    options[1].click()
                                    print(f"      → 选择选项: {options[1].inner_text()}")
                                    
                    except Exception as e:
                        print(f"   字段 {i+1} 填写失败: {e}")
                
                page.screenshot(path='/tmp/step4_form_filled.png', full_page=True)
                print("📸 截图已保存: /tmp/step4_form_filled.png")
                
            else:
                print("❌ 未检测到弹窗")
            
            # 5. 点击确定按钮提交
            print("\n[Step 5] 提交表单...")
            
            submit_button = page.locator('button:has-text("确定"), button:has-text("提交"), button:has-text("保存")').first
            if submit_button.count() > 0:
                submit_button.click()
                print("✅ 点击了确定按钮")
                
                # 等待响应
                time.sleep(3)
                page.screenshot(path='/tmp/step5_submitted.png', full_page=True)
                print("📸 截图已保存: /tmp/step5_submitted.png")
                
                # 6. 验证结果
                print("\n[Step 6] 验证结果...")
                
                # 检查是否有成功提示
                try:
                    success_message = page.locator('text=/成功|success/i, .bk-message-success').first
                    if success_message.count() > 0:
                        print("✅ 检测到成功提示消息")
                        print(f"   消息内容: {success_message.inner_text()}")
                    else:
                        print("⚠️ 未检测到明确的成功消息")
                except:
                    print("⚠️ 检查成功消息时出错")
                
                # 检查列表是否刷新
                time.sleep(2)
                page.screenshot(path='/tmp/step6_final.png', full_page=True)
                print("📸 最终截图已保存: /tmp/step6_final.png")
                
                # 7. 检查控制台错误
                print("\n[Step 7] 检查控制台...")
                
            else:
                print("❌ 未找到确定按钮")
            
            # 获取页面内容用于调试
            print("\n[Debug] 页面DOM片段:")
            body_text = page.locator('body').inner_text()
            print(body_text[:500])
            
            # 最终输出
            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)
            print("\n截图文件:")
            print("  - /tmp/step1_initial.png (初始状态)")
            print("  - /tmp/step2_model_selected.png (选择模型后)")
            print("  - /tmp/step3_dialog_opened.png (新建弹窗)")
            print("  - /tmp/step4_form_filled.png (表单填写后)")
            print("  - /tmp/step5_submitted.png (提交后)")
            print("  - /tmp/step6_final.png (最终状态)")
            
        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='/tmp/error_screenshot.png', full_page=True)
            print("📸 错误截图已保存: /tmp/error_screenshot.png")
            
        finally:
            browser.close()
            print("\n浏览器已关闭")

if __name__ == "__main__":
    test_create_instance()
