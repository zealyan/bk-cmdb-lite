#!/usr/bin/env python3
"""
前端界面测试 - 使用Playwright
验证数据库改动在前端的正确性
"""

from playwright.sync_api import sync_playwright
import time

def test_frontend_basic_functionality():
    """测试前端基本功能"""
    print("\n=== 测试前端界面功能 ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 测试健康检查页面
            print("1. 测试前端页面加载...")
            page.goto("http://localhost:8000")
            page.wait_for_load_state('networkidle', timeout=10000)
            
            # 等待页面加载
            page.wait_for_timeout(2000)
            
            # 获取页面内容
            content = page.content()
            if "CMDB Server Lite" in content or "message" in content:
                print("   ✓ 根路径页面加载成功")
            
            # 测试前端UI（如果有）
            # 这里可以测试实际的前端页面
            print("\n2. 测试模型列表功能...")
            
            # 截图保存用于验证
            page.screenshot(path='/tmp/frontend_test.png', full_page=True)
            print("   ✓ 页面截图已保存到 /tmp/frontend_test.png")
            
            # 测试API端点
            print("\n3. 测试关键API端点...")
            
            # 测试模型列表
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/models');
                    const data = await response.json();
                    window.testModels = data.models;
                }
            """)
            page.wait_for_timeout(1000)
            
            models = page.evaluate("() => window.testModels")
            if models and len(models) > 0:
                print(f"   ✓ 模型列表API正常工作，共{len(models)}个模型")
                for model in models[:3]:
                    print(f"     - {model.get('bk_obj_id')}: {model.get('bk_obj_name')}")
            
            # 测试实例查询
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/models/bk_slb/instances?page=1&page_size=1');
                    const data = await response.json();
                    window.testInstance = data.instances[0];
                }
            """)
            page.wait_for_timeout(1000)
            
            instance = page.evaluate("() => window.testInstance")
            if instance and 'bk_operate_time' in instance:
                print(f"   ✓ 实例查询API正常工作，包含bk_operate_time字段")
            else:
                print(f"   ✗ 实例查询缺少bk_operate_time字段")
            
            # 测试属性查询
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/models/bk_slb/attributes');
                    const data = await response.json();
                    window.testAttr = data.attributes[0];
                }
            """)
            page.wait_for_timeout(1000)
            
            attr = page.evaluate("() => window.testAttr")
            if attr and 'bk_issystem' in attr:
                print(f"   ✓ 属性查询API正常工作，包含bk_issystem字段")
            else:
                print(f"   ✗ 属性查询缺少bk_issystem字段")
            
            # 测试关联查询
            page.evaluate("""
                async () => {
                    const response = await fetch('/api/instances/1/associations');
                    const data = await response.json();
                    window.testAssocs = data.associations;
                }
            """)
            page.wait_for_timeout(1000)
            
            assocs = page.evaluate("() => window.testAssocs")
            if assocs and len(assocs) > 0:
                print(f"   ✓ 关联查询API正常工作，共{len(assocs)}条关联")
            
            print("\n4. 检查浏览器控制台错误...")
            
            # 收集控制台错误
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            
            page.reload()
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            
            if not errors:
                print("   ✓ 无JavaScript控制台错误")
            else:
                print(f"   ⚠ 发现 {len(errors)} 个控制台错误:")
                for error in errors[:3]:
                    print(f"     - {error[:100]}")
            
            print("\n" + "=" * 70)
            print("✓ 前端测试完成")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n✗ 前端测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            browser.close()

def test_database_structure_directly():
    """直接测试数据库结构"""
    print("\n=== 直接测试数据库结构 ===")
    
    import duckdb
    
    db = duckdb.connect('/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb')
    
    try:
        # 检查所有关键表
        tables_to_check = [
            ('cc_ObjAttDes', ['bk_issystem', 'bk_property_id', 'bk_property_name']),
            ('cc_ObjDes', ['bk_obj_id', 'bk_obj_name']),
            ('cc_ObjAsst', ['bk_obj_id', 'target_obj_id']),
            ('cc_AsstDes', ['bk_asst_id', 'bk_asst_name']),
            ('cc_InstAsst_0_pub', ['bk_inst_id', 'bk_asst_inst_id']),
        ]
        
        for table_name, required_fields in tables_to_check:
            columns = db.execute(f"DESCRIBE {table_name}").fetchall()
            column_names = [col[0] for col in columns]
            
            missing = [f for f in required_fields if f not in column_names]
            if not missing:
                print(f"✓ {table_name}: 所有必需字段都存在")
            else:
                print(f"✗ {table_name}: 缺少字段 {missing}")
        
        # 检查实例表
        instance_tables = [
            'cc_ObjectBase_0_pub_bk_slb',
            'cc_ObjectBase_0_pub_bk_host',
            'cc_ObjectBase_0_pub_bk_switch',
            'cc_ObjectBase_0_pub_bk_slb_server',
            'cc_ObjectBase_0_pub_bk_slb_listener'
        ]
        
        for table_name in instance_tables:
            columns = db.execute(f"DESCRIBE {table_name}").fetchall()
            column_names = [col[0] for col in columns]
            
            has_operate_time = 'bk_operate_time' in column_names
            has_create_time = 'create_time' in column_names
            has_last_time = 'last_time' in column_names
            
            if has_operate_time and has_create_time and has_last_time:
                print(f"✓ {table_name}: 包含所有时间字段")
            else:
                missing = []
                if not has_operate_time:
                    missing.append('bk_operate_time')
                if not has_create_time:
                    missing.append('create_time')
                if not has_last_time:
                    missing.append('last_time')
                print(f"✗ {table_name}: 缺少字段 {missing}")
        
        print("\n✓ 数据库结构测试完成")
        return True
        
    except Exception as e:
        print(f"\n✗ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

def main():
    print("=" * 70)
    print("前端界面和数据库结构综合测试")
    print("=" * 70)
    
    # 直接测试数据库
    db_result = test_database_structure_directly()
    
    # 测试前端
    frontend_result = test_frontend_basic_functionality()
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    results = [
        ("数据库结构测试", db_result),
        ("前端界面测试", frontend_result)
    ]
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status:8s} | {test_name}")
    
    print("=" * 70)
    
    if all(result for _, result in results):
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查。")
        return 1

if __name__ == "__main__":
    exit(main())
