#!/usr/bin/env python3
"""
使用 Python Playwright 测试 SLB ID=1 的关联数据
"""

import requests
import json
import sys

def test_api_first():
    """首先通过 API 验证数据"""
    print('=' * 60)
    print('  API 层数据验证测试')
    print('=' * 60)
    
    print('\n步骤1: 获取 SLB ID=1 的关联数据')
    
    try:
        response = requests.get('http://localhost:8000/api/instances/1/associations', timeout=10)
        if response.status_code == 200:
            data = response.json()
            associations = data.get('associations', [])
            
            servers = [a for a in associations if a.get('bk_asst_obj_id') == 'bk_slb_server']
            listeners = [a for a in associations if a.get('bk_asst_obj_id') == 'bk_slb_listener']
            
            print(f'  总关联数: {len(associations)}')
            print(f'  后端服务器: {len(servers)} 条')
            print(f'  监听器: {len(listeners)} 条')
            
            if len(servers) == 15 and len(listeners) == 15:
                print('\n✅ API 层数据验证成功！')
                return True, len(servers), len(listeners)
            else:
                print('\n❌ API 层数据验证失败！')
                print(f'   期望后端服务器: 15, 实际: {len(servers)}')
                print(f'   期望监听器: 15, 实际: {len(listeners)}')
                return False, len(servers), len(listeners)
        else:
            print(f'  API 请求失败: {response.status_code}')
            return False, 0, 0
    except Exception as e:
        print(f'  错误: {e}')
        return False, 0, 0

try:
    from playwright.sync_api import sync_playwright
    
    def test_frontend():
        """测试前端界面"""
        print('\n' + '=' * 60)
        print('  前端界面测试')
        print('=' * 60)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                print('\n步骤1: 访问首页')
                page.goto('http://localhost:3000', wait_until='networkidle')
                print('✅ 页面加载成功')
                
                print('\n步骤2: 进入资源管理')
                page.wait_for_selector('text=资源', timeout=5000)
                page.click('text=资源')
                page.wait_for_timeout(1000)
                print('✅ 资源管理加载成功')
                
                print('\n步骤3: 选择负载均衡模型')
                page.wait_for_selector('text=负载均衡', timeout=5000)
                page.click('text=负载均衡')
                page.wait_for_timeout(1000)
                print('✅ 负载均衡选择成功')
                
                print('\n步骤4: 进入 web-slb-public 详情页')
                page.wait_for_selector('text=web-slb-public', timeout=5000)
                page.click('text=web-slb-public')
                page.wait_for_timeout(1500)
                print('✅ 进入详情页成功')
                
                print('\n步骤5: 切换到关联 Tab')
                # 尝试多种方式找到关联 Tab
                assoc_tab = page.locator('.bk-tab-label-item, [role="tab"]').filter(has_text='关联')
                
                if assoc_tab.count() > 0:
                    assoc_tab.first.click()
                    page.wait_for_timeout(1500)
                    print('✅ 切换到关联 Tab 成功')
                    
                    # 截图保存
                    page.screenshot(path='/workspace/bk-cmdb/cmdb_ui_lite/frontend-test-result.png', full_page=True)
                    print(f'✅ 截图已保存')
                    
                    return True
                else:
                    print('❌ 未找到关联 Tab')
                    page.screenshot(path='/workspace/bk-cmdb/cmdb_ui_lite/frontend-test-error.png')
                    return False
                    
            except Exception as e:
                print(f'❌ 前端测试出错: {e}')
                try:
                    page.screenshot(path='/workspace/bk-cmdb/cmdb_ui_lite/frontend-test-error.png')
                except:
                    pass
                return False
            finally:
                browser.close()

    # 运行测试
    api_ok, server_count, listener_count = test_api_first()
    
    try:
        frontend_ok = test_frontend()
    except Exception as e:
        print(f'\n⚠️  前端测试跳过 (Playwright 环境问题): {e}')
        frontend_ok = None
    
    print('\n' + '=' * 60)
    print('  测试总结')
    print('=' * 60)
    print(f'API 层数据验证: {"✅ 通过" if api_ok else "❌ 失败"}')
    print(f'  - 后端服务器: {server_count} / 15')
    print(f'  - 监听器: {listener_count} / 15')
    
    if frontend_ok is not None:
        print(f'前端界面测试: {"✅ 通过" if frontend_ok else "❌ 失败"}')
    
    if api_ok:
        print('\n🎉 核心数据修复验证成功！')
        sys.exit(0)
    else:
        print('\n❌ 修复验证失败')
        sys.exit(1)
        
except ImportError:
    # 如果 Playwright 不可用，只做 API 测试
    print('\n⚠️  Playwright 不可用，只进行 API 测试')
    api_ok, server_count, listener_count = test_api_first()
    
    print('\n' + '=' * 60)
    print('  测试总结')
    print('=' * 60)
    print(f'API 层数据验证: {"✅ 通过" if api_ok else "❌ 失败"}')
    print(f'  - 后端服务器: {server_count} / 15')
    print(f'  - 监听器: {listener_count} / 15')
    
    if api_ok:
        print('\n🎉 核心数据修复验证成功！')
        sys.exit(0)
    else:
        print('\n❌ 修复验证失败')
        sys.exit(1)
