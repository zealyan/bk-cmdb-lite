#!/usr/bin/env python3
"""
测试关联 Tab 调试功能
验证 SLB ID=1 的关联数据是否正确显示
"""

import requests
import json
import sys

def test_api_data():
    """测试 API 数据"""
    print('=' * 70)
    print('  API 数据验证测试')
    print('=' * 70)
    
    results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    # 测试1: 获取 SLB ID=1 的关联数据
    print('\n【测试1】获取 SLB ID=1 的关联数据')
    try:
        response = requests.get(
            'http://localhost:8000/api/instances/1/associations',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            associations = data.get('associations', [])
            servers = [a for a in associations if a.get('bk_asst_obj_id') == 'bk_slb_server']
            listeners = [a for a in associations if a.get('bk_asst_obj_id') == 'bk_slb_listener']
            
            print(f'  ✅ 成功! 总关联: {len(associations)}')
            print(f'     后端服务器: {len(servers)} 条')
            print(f'     监听器: {len(listeners)} 条')
            
            results['tests'].append({
                'name': '获取关联数据',
                'status': 'pass',
                'details': f'总数{len(associations)}, 服务器{len(servers)}, 监听器{len(listeners)}'
            })
            results['passed'] += 1
        else:
            print(f'  ❌ 失败: {response.status_code}')
            results['tests'].append({'name': '获取关联数据', 'status': 'fail'})
            results['failed'] += 1
    except Exception as e:
        print(f'  ❌ 错误: {e}')
        results['tests'].append({'name': '获取关联数据', 'status': 'fail', 'error': str(e)})
        results['failed'] += 1
    
    # 测试2: 获取关系定义
    print('\n【测试2】获取关系定义')
    try:
        response = requests.get(
            'http://localhost:8000/api/relations',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            relations = data.get('relations', [])
            print(f'  ✅ 成功! 关系定义: {len(relations)} 条')
            for r in relations[:3]:
                print(f'     - {r.get("bk_relation_type_id")}: {r.get("bk_relation_type_name")}')
            
            results['tests'].append({
                'name': '获取关系定义',
                'status': 'pass',
                'details': f'{len(relations)}条'
            })
            results['passed'] += 1
        else:
            print(f'  ❌ 失败: {response.status_code}')
            results['tests'].append({'name': '获取关系定义', 'status': 'fail'})
            results['failed'] += 1
    except Exception as e:
        print(f'  ❌ 错误: {e}')
        results['tests'].append({'name': '获取关系定义', 'status': 'fail', 'error': str(e)})
        results['failed'] += 1
    
    # 测试3: 获取各模型的实例数据
    print('\n【测试3】获取各模型的实例数据')
    models = ['bk_slb', 'bk_slb_server', 'bk_slb_listener']
    for model_id in models:
        try:
            response = requests.get(
                f'http://localhost:8000/api/models/{model_id}/instances',
                params={'page': 1, 'page_size': 100},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                print(f'  ✅ {model_id}: {total} 条')
                results['passed'] += 1
            else:
                print(f'  ❌ {model_id}: {response.status_code}')
                results['failed'] += 1
        except Exception as e:
            print(f'  ❌ {model_id}: {e}')
            results['failed'] += 1
    
    # 测试4: 获取模型属性
    print('\n【测试4】获取模型属性')
    for model_id in models:
        try:
            response = requests.get(
                f'http://localhost:8000/api/models/{model_id}/attributes',
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                attrs = data.get('attributes', [])
                print(f'  ✅ {model_id}: {len(attrs)} 个属性')
                results['passed'] += 1
            else:
                print(f'  ❌ {model_id}: {response.status_code}')
                results['failed'] += 1
        except Exception as e:
            print(f'  ❌ {model_id}: {e}')
            results['failed'] += 1
    
    return results

def test_frontend_with_playwright():
    """使用 Playwright 测试前端"""
    print('\n' + '=' * 70)
    print('  前端界面测试 (Playwright)')
    print('=' * 70)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 收集控制台日志
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))
            
            try:
                print('\n步骤1: 访问首页')
                page.goto('http://localhost:3000', wait_until='networkidle', timeout=30000)
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
                page.wait_for_timeout(2000)
                print('✅ 进入详情页成功')
                
                print('\n步骤5: 切换到关联 Tab')
                assoc_tab = page.locator('.bk-tab-label-item, [role="tab"]').filter(has_text='关联')
                
                if assoc_tab.count() > 0:
                    assoc_tab.first.click()
                    page.wait_for_timeout(2000)
                    print('✅ 切换到关联 Tab 成功')
                    
                    # 截图
                    screenshot_path = '/workspace/bk-cmdb/cmdb_ui_lite/association-debug-test.png'
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f'✅ 截图已保存: {screenshot_path}')
                    
                    # 检查调试信息面板
                    debug_panel = page.locator('.debug-info')
                    if debug_panel.count() > 0:
                        print('\n✅ 发现调试信息面板!')
                        debug_text = debug_panel.first.text_content()
                        print(f'调试信息内容:\n{debug_text}')
                    else:
                        print('\n⚠️  未发现调试信息面板')
                    
                    # 检查关联组
                    groups = page.locator('.association-group')
                    group_count = groups.count()
                    print(f'\n关联组数量: {group_count}')
                    
                    # 输出控制台日志
                    print('\n控制台日志 (InstanceAssociation):')
                    for log in console_logs:
                        if 'InstanceAssociation' in log or 'DEBUG' in log:
                            print(f'  {log}')
                    
                    return True
                else:
                    print('❌ 未找到关联 Tab')
                    page.screenshot(path='/workspace/bk-cmdb/cmdb_ui_lite/association-test-error.png')
                    return False
                    
            except Exception as e:
                print(f'❌ 测试出错: {e}')
                try:
                    page.screenshot(path='/workspace/bk-cmdb/cmdb_ui_lite/association-test-error.png')
                except:
                    pass
                return False
            finally:
                browser.close()
                
    except ImportError:
        print('\n⚠️  Playwright 不可用，跳过前端测试')
        return None
    except Exception as e:
        print(f'\n⚠️  前端测试跳过: {e}')
        return None

def main():
    """主测试流程"""
    print('=' * 70)
    print('  🔍 关联 Tab 调试功能测试')
    print('=' * 70)
    
    # API 测试
    api_results = test_api_data()
    
    # 前端测试
    frontend_result = test_frontend_with_playwright()
    
    # 总结
    print('\n' + '=' * 70)
    print('  📊 测试总结')
    print('=' * 70)
    print(f'API 测试: ✅ {api_results["passed"]} 通过, ❌ {api_results["failed"]} 失败')
    
    if frontend_result is True:
        print('前端测试: ✅ 通过')
    elif frontend_result is False:
        print('前端测试: ❌ 失败')
    else:
        print('前端测试: ⚠️  跳过')
    
    print('\n' + '=' * 70)
    
    if api_results['failed'] == 0:
        print('✅ API 数据验证成功!')
        return 0
    else:
        print('❌ 存在测试失败')
        return 1

if __name__ == '__main__':
    sys.exit(main())
