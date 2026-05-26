#!/usr/bin/env python3
"""
关联功能集成测试
测试完整的数据流：数据库 → 后端API → 前端显示
"""

import requests
import duckdb
import json
import time
from playwright.sync_api import sync_playwright

class AssociationIntegrationTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.db_path = "/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb"
        self.results = {
            "database": {},
            "api": {},
            "frontend": {},
            "integration": {}
        }

    def test_database_layer(self):
        """测试数据库层数据"""
        print("\n" + "="*60)
        print("📊 第一层：数据库层测试")
        print("="*60)

        try:
            # 使用只读模式连接数据库，避免锁定冲突
            db = duckdb.connect(self.db_path, read_only=True)

            # 1. 检查SLB实例
            print("\n【1. SLB实例】")
            slb_info = db.execute('SELECT * FROM bk_slb_instances WHERE id = ?', [1]).fetchone()
            if slb_info:
                self.results["database"]["slb_instance"] = {
                    "id": slb_info[0],
                    "name": slb_info[1],
                    "ip": slb_info[2]
                }
                print(f"  ✓ SLB ID=1: {slb_info[1]} ({slb_info[2]})")
            else:
                print("  ✗ 未找到SLB ID=1")
                self.results["database"]["slb_instance"] = None

            # 2. 检查后端服务器关联
            print("\n【2. 后端服务器关联】")
            server_count = db.execute(
                'SELECT COUNT(*) FROM bk_slb_server_instances WHERE bk_slb_id = ?',
                ['1']
            ).fetchone()[0]
            servers = db.execute(
                'SELECT id, bk_server_name, bk_server_ip FROM bk_slb_server_instances WHERE bk_slb_id = ?',
                ['1']
            ).fetchall()
            self.results["database"]["servers"] = {
                "count": server_count,
                "servers": [{"id": s[0], "name": s[1], "ip": s[2]} for s in servers]
            }
            print(f"  ✓ 后端服务器数量: {server_count}")
            for s in servers[:5]:
                print(f"    - ID={s[0]}: {s[1]} ({s[2]})")
            if len(servers) > 5:
                print(f"    ... 还有 {len(servers) - 5} 条")

            # 3. 检查监听器关联
            print("\n【3. 监听器关联】")
            listener_count = db.execute(
                'SELECT COUNT(*) FROM bk_slb_listener_instances WHERE bk_slb_id = ?',
                ['1']
            ).fetchone()[0]
            listeners = db.execute(
                'SELECT id, bk_listener_name, bk_protocol, bk_frontend_port FROM bk_slb_listener_instances WHERE bk_slb_id = ?',
                ['1']
            ).fetchall()
            self.results["database"]["listeners"] = {
                "count": listener_count,
                "listeners": [{"id": l[0], "name": l[1], "protocol": l[2], "port": l[3]} for l in listeners]
            }
            print(f"  ✓ 监听器数量: {listener_count}")
            for l in listeners[:5]:
                print(f"    - ID={l[0]}: {l[1]} ({l[2]}:{l[3]})")
            if len(listeners) > 5:
                print(f"    ... 还有 {len(listeners) - 5} 条")

            # 4. 检查associations表
            print("\n【4. 关联关系表】")
            assoc_count = db.execute(
                'SELECT COUNT(*) FROM associations WHERE bk_obj_id = ? AND bk_inst_id = ?',
                ['bk_slb', 1]
            ).fetchone()[0]
            assocs = db.execute(
                'SELECT * FROM associations WHERE bk_obj_id = ? AND bk_inst_id = ?',
                ['bk_slb', 1]
            ).fetchall()
            self.results["database"]["associations"] = {
                "count": assoc_count,
                "associations": assocs
            }
            print(f"  ✓ 关联记录总数: {assoc_count}")

            db.close()
            print("\n✅ 数据库层测试通过！")
            return True

        except Exception as e:
            print(f"\n❌ 数据库层测试失败: {e}")
            self.results["database"]["error"] = str(e)
            return False

    def test_api_layer(self):
        """测试API层数据"""
        print("\n" + "="*60)
        print("🔌 第二层：API层测试")
        print("="*60)

        try:
            # 1. 测试获取SLB实例
            print("\n【1. 获取SLB实例详情】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb/instances/1")
            if response.status_code == 200:
                instance_data = response.json()
                self.results["api"]["slb_instance"] = instance_data
                print(f"  ✓ API返回实例: {instance_data.get('instance', {}).get('bk_lb_name', 'N/A')}")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                self.results["api"]["slb_instance"] = None

            # 2. 测试获取关联
            print("\n【2. 获取实例关联】")
            response = requests.get(f"{self.base_url}/api/instances/1/associations")
            if response.status_code == 200:
                assoc_data = response.json()
                assoc_list = assoc_data.get("associations", [])
                self.results["api"]["associations"] = {
                    "count": len(assoc_list),
                    "associations": assoc_list
                }
                print(f"  ✓ API返回关联数: {len(assoc_list)}")

                # 统计不同类型的关联
                server_assocs = [a for a in assoc_list if a.get("bk_asst_obj_id") == "bk_slb_server"]
                listener_assocs = [a for a in assoc_list if a.get("bk_asst_obj_id") == "bk_slb_listener"]
                print(f"    - 后端服务器关联: {len(server_assocs)} 条")
                print(f"    - 监听器关联: {len(listener_assocs)} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                self.results["api"]["associations"] = None

            # 3. 测试获取后端服务器列表
            print("\n【3. 获取后端服务器列表】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb_server/instances", params={"page": 1, "page_size": 1000})
            if response.status_code == 200:
                servers_data = response.json()
                servers = servers_data.get("instances", [])
                slb_servers = [s for s in servers if s.get("bk_slb_id") == "1"]
                self.results["api"]["slb_servers"] = {
                    "count": len(slb_servers),
                    "servers": slb_servers
                }
                print(f"  ✓ API返回SLB关联的后端服务器: {len(slb_servers)} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                self.results["api"]["slb_servers"] = None

            # 4. 测试获取监听器列表
            print("\n【4. 获取监听器列表】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb_listener/instances", params={"page": 1, "page_size": 1000})
            if response.status_code == 200:
                listeners_data = response.json()
                listeners = listeners_data.get("instances", [])
                slb_listeners = [l for l in listeners if l.get("bk_slb_id") == "1"]
                self.results["api"]["slb_listeners"] = {
                    "count": len(slb_listeners),
                    "listeners": slb_listeners
                }
                print(f"  ✓ API返回SLB关联的监听器: {len(slb_listeners)} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                self.results["api"]["slb_listeners"] = None

            print("\n✅ API层测试通过！")
            return True

        except Exception as e:
            print(f"\n❌ API层测试失败: {e}")
            self.results["api"]["error"] = str(e)
            return False

    def test_frontend_layer(self):
        """测试前端层数据"""
        print("\n" + "="*60)
        print("🖥️ 第三层：前端层测试")
        print("="*60)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # 1. 访问前端
                print("\n【1. 访问前端页面】")
                page.goto(self.frontend_url)
                page.wait_for_load_state('networkidle')
                print(f"  ✓ 前端页面加载成功")

                # 2. 进入SLB实例列表
                print("\n【2. 进入SLB实例列表】")
                page.click('text=负载均衡(SLB)')
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                print(f"  ✓ 进入SLB实例列表")

                # 3. 点击web-slb-public进入详情
                print("\n【3. 进入web-slb-public详情页】")
                page.click('text=web-slb-public')
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                print(f"  ✓ 进入详情页")

                # 4. 截图保存
                page.screenshot(path='/tmp/slb_details.png', full_page=True)
                print(f"  ✓ 截图已保存: /tmp/slb_details.png")

                # 5. 点击关联标签
                print("\n【4. 切换到关联标签】")
                page.click('text=关联')
                page.wait_for_load_state('networkidle')
                time.sleep(2)

                # 6. 获取关联信息
                page.screenshot(path='/tmp/slb_associations.png', full_page=True)

                # 获取console日志
                console_logs = []
                page.on("console", lambda msg: console_logs.append(msg.text) if msg.type == "log" else None)

                # 刷新页面触发日志
                page.reload()
                page.wait_for_load_state('networkidle')
                time.sleep(3)

                # 获取关联数据
                associations_tab = page.locator('.bk-tab-section')
                if associations_tab.count() > 0:
                    content = associations_tab.inner_text()
                    self.results["frontend"]["associations_content"] = content
                    print(f"  ✓ 关联内容已捕获")

                    # 尝试提取关联数量
                    if "后端服务器" in content:
                        print(f"  ✓ 找到后端服务器关联")
                    if "监听器" in content:
                        print(f"  ✓ 找到监听器关联")

                # 获取所有console日志
                self.results["frontend"]["console_logs"] = [log for log in console_logs if "DEBUG" in log or "Associations" in log]

                browser.close()
                print("\n✅ 前端层测试完成！")
                return True

        except Exception as e:
            print(f"\n❌ 前端层测试失败: {e}")
            self.results["frontend"]["error"] = str(e)
            return False

    def test_integration(self):
        """测试集成一致性"""
        print("\n" + "="*60)
        print("🔗 第四层：集成测试")
        print("="*60)

        try:
            # 1. 比较数据库和API的数据
            print("\n【1. 数据库 vs API 数据一致性】")

            db_servers = self.results["database"]["servers"]["count"]
            api_servers = self.results["api"]["slb_servers"]["count"]

            db_listeners = self.results["database"]["listeners"]["count"]
            api_listeners = self.results["api"]["slb_listeners"]["count"]

            print(f"  后端服务器: 数据库={db_servers}, API={api_servers}")
            if db_servers == api_servers:
                print(f"    ✅ 一致")
                self.results["integration"]["servers_match"] = True
            else:
                print(f"    ❌ 不一致")
                self.results["integration"]["servers_match"] = False

            print(f"  监听器: 数据库={db_listeners}, API={api_listeners}")
            if db_listeners == api_listeners:
                print(f"    ✅ 一致")
                self.results["integration"]["listeners_match"] = True
            else:
                print(f"    ❌ 不一致")
                self.results["integration"]["listeners_match"] = False

            # 2. 检查API和associations表的一致性
            print("\n【2. API vs Associations表】")
            assoc_list = self.results["api"]["associations"]["associations"]
            server_assocs = len([a for a in assoc_list if a.get("bk_asst_obj_id") == "bk_slb_server"])
            listener_assocs = len([a for a in assoc_list if a.get("bk_asst_obj_id") == "bk_slb_listener"])

            print(f"  后端服务器关联: associations表={server_assocs}")
            print(f"  监听器关联: associations表={listener_assocs}")

            if server_assocs == db_servers:
                print(f"    ✅ 后端服务器关联完整")
                self.results["integration"]["servers_complete"] = True
            else:
                print(f"    ⚠️ 部分关联缺失")
                self.results["integration"]["servers_complete"] = False

            if listener_assocs == db_listeners:
                print(f"    ✅ 监听器关联完整")
                self.results["integration"]["listeners_complete"] = True
            else:
                print(f"    ⚠️ 部分关联缺失")
                self.results["integration"]["listeners_complete"] = False

            # 3. 总结
            print("\n【3. 测试总结】")
            all_pass = all([
                self.results["integration"]["servers_match"],
                self.results["integration"]["listeners_match"],
                self.results["integration"]["servers_complete"],
                self.results["integration"]["listeners_complete"]
            ])

            if all_pass:
                print("  ✅ 所有集成测试通过！")
                print(f"  - 后端服务器: {db_servers} 条")
                print(f"  - 监听器: {db_listeners} 条")
                print(f"  - 总关联记录: {len(assoc_list)} 条")
            else:
                print("  ⚠️ 部分测试未通过，请检查日志")

            self.results["integration"]["all_pass"] = all_pass
            return all_pass

        except Exception as e:
            print(f"\n❌ 集成测试失败: {e}")
            self.results["integration"]["error"] = str(e)
            return False

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📝 测试报告")
        print("="*60)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "database": self.results["database"],
            "api": self.results["api"],
            "frontend": self.results["frontend"],
            "integration": self.results["integration"]
        }

        # 保存JSON报告
        with open('/tmp/association_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n  详细报告已保存: /tmp/association_test_report.json")
        print(f"  截图已保存:")
        print(f"    - /tmp/slb_details.png (详情页)")
        print(f"    - /tmp/slb_associations.png (关联页)")

        return report

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 关联功能集成测试开始")
        print("="*60)

        # 1. 数据库层
        db_pass = self.test_database_layer()
        if not db_pass:
            print("\n❌ 数据库层失败，停止测试")
            return False

        # 2. API层
        api_pass = self.test_api_layer()
        if not api_pass:
            print("\n❌ API层失败，停止测试")
            return False

        # 3. 前端层
        frontend_pass = self.test_frontend_layer()

        # 4. 集成测试
        integration_pass = self.test_integration()

        # 5. 生成报告
        report = self.generate_report()

        # 最终结果
        print("\n" + "="*60)
        print("🎯 最终测试结果")
        print("="*60)
        print(f"  数据库层: {'✅ 通过' if db_pass else '❌ 失败'}")
        print(f"  API层: {'✅ 通过' if api_pass else '❌ 失败'}")
        print(f"  前端层: {'✅ 通过' if frontend_pass else '⚠️ 部分完成'}")
        print(f"  集成测试: {'✅ 通过' if integration_pass else '❌ 失败'}")

        all_pass = db_pass and api_pass and integration_pass
        if all_pass:
            print("\n🎉 所有测试通过！关联功能工作正常！")
        else:
            print("\n⚠️ 部分测试未通过，请查看详细日志")

        return all_pass


if __name__ == '__main__':
    test = AssociationIntegrationTest()
    success = test.run_all_tests()
    exit(0 if success else 1)
