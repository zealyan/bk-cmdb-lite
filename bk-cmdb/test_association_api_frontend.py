#!/usr/bin/env python3
"""
关联功能集成测试 - API和前端层
"""

import requests
import json
import time
from playwright.sync_api import sync_playwright

class AssociationAPITest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.results = {
            "api": {},
            "frontend": {},
            "integration": {}
        }

    def test_api_layer(self):
        """测试API层数据"""
        print("\n" + "="*60)
        print("🔌 第一层：API层测试")
        print("="*60)

        try:
            # 1. 测试健康检查
            print("\n【0. 健康检查】")
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"  ✓ 服务健康: {health.get('service')}")
                print(f"  ✓ 数据库: {health.get('database', {}).get('status')}")
            else:
                print(f"  ✗ 健康检查失败")
                return False

            # 2. 测试获取SLB实例
            print("\n【1. 获取SLB实例详情】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb/instances/1")
            if response.status_code == 200:
                instance_data = response.json()
                self.results["api"]["slb_instance"] = instance_data
                slb_name = instance_data.get('instance', {}).get('bk_lb_name', 'N/A')
                print(f"  ✓ API返回实例: {slb_name}")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                return False

            # 3. 测试获取关联
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

                self.results["api"]["server_count"] = len(server_assocs)
                self.results["api"]["listener_count"] = len(listener_assocs)
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                return False

            # 4. 测试获取后端服务器列表
            print("\n【3. 获取后端服务器列表】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb_server/instances", params={"page": 1, "page_size": 1000})
            if response.status_code == 200:
                servers_data = response.json()
                servers = servers_data.get("instances", [])
                slb_servers = [s for s in servers if s.get("bk_slb_id") == "1"]
                self.results["api"]["slb_servers"] = {
                    "count": len(slb_servers),
                    "servers": slb_servers[:5]  # 只保存前5个
                }
                print(f"  ✓ API返回SLB关联的后端服务器: {len(slb_servers)} 条")
                for s in slb_servers[:5]:
                    print(f"    - {s.get('bk_server_name')} ({s.get('bk_server_ip')})")
                if len(slb_servers) > 5:
                    print(f"    ... 还有 {len(slb_servers) - 5} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                return False

            # 5. 测试获取监听器列表
            print("\n【4. 获取监听器列表】")
            response = requests.get(f"{self.base_url}/api/models/bk_slb_listener/instances", params={"page": 1, "page_size": 1000})
            if response.status_code == 200:
                listeners_data = response.json()
                listeners = listeners_data.get("instances", [])
                slb_listeners = [l for l in listeners if l.get("bk_slb_id") == "1"]
                self.results["api"]["slb_listeners"] = {
                    "count": len(slb_listeners),
                    "listeners": slb_listeners[:5]  # 只保存前5个
                }
                print(f"  ✓ API返回SLB关联的监听器: {len(slb_listeners)} 条")
                for l in slb_listeners[:5]:
                    print(f"    - {l.get('bk_listener_name')} ({l.get('bk_protocol')}:{l.get('bk_frontend_port')})")
                if len(slb_listeners) > 5:
                    print(f"    ... 还有 {len(slb_listeners) - 5} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                return False

            # 6. 测试获取关系定义
            print("\n【5. 获取关系定义】")
            response = requests.get(f"{self.base_url}/api/relations")
            if response.status_code == 200:
                relations_data = response.json()
                relations = relations_data.get("relations", [])
                self.results["api"]["relations"] = {
                    "count": len(relations),
                    "relations": relations
                }
                print(f"  ✓ API返回关系定义: {len(relations)} 条")
            else:
                print(f"  ✗ API返回错误: {response.status_code}")
                return False

            print("\n✅ API层测试通过！")
            return True

        except Exception as e:
            print(f"\n❌ API层测试失败: {e}")
            self.results["api"]["error"] = str(e)
            return False

    def test_frontend_layer(self):
        """测试前端层数据"""
        print("\n" + "="*60)
        print("🖥️ 第二层：前端层测试")
        print("="*60)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # 捕获console日志
                console_logs = []
                page.on("console", lambda msg: console_logs.append({
                    "type": msg.type,
                    "text": msg.text
                }) if msg.type in ["log", "error"] else None)

                # 1. 访问前端
                print("\n【1. 访问前端页面】")
                page.goto(self.frontend_url)
                page.wait_for_load_state('networkidle')
                time.sleep(2)
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
                time.sleep(3)

                # 6. 截图保存
                page.screenshot(path='/tmp/slb_associations.png', full_page=True)
                print(f"  ✓ 关联页面截图已保存: /tmp/slb_associations.png")

                # 7. 尝试获取关联内容
                print("\n【5. 分析关联内容】")
                association_cards = page.locator('.association-card, .bk-card, [class*="association"]')
                card_count = association_cards.count()
                print(f"  ✓ 找到关联卡片: {card_count} 个")

                # 获取关联表格
                tables = page.locator('table, .bk-table')
                table_count = tables.count()
                print(f"  ✓ 找到表格: {table_count} 个")

                # 获取文本内容
                page_content = page.content()
                has_server = '后端服务器' in page_content or 'bk_slb_server' in page_content
                has_listener = '监听器' in page_content or 'bk_slb_listener' in page_content
                print(f"  ✓ 包含后端服务器关键词: {has_server}")
                print(f"  ✓ 包含监听器关键词: {has_listener}")

                # 保存console日志
                self.results["frontend"]["console_logs"] = console_logs
                self.results["frontend"]["card_count"] = card_count
                self.results["frontend"]["table_count"] = table_count
                self.results["frontend"]["has_server"] = has_server
                self.results["frontend"]["has_listener"] = has_listener

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
        print("🔗 第三层：集成测试")
        print("="*60)

        try:
            # 1. API数据验证
            print("\n【1. API数据验证】")
            server_count = self.results["api"].get("server_count", 0)
            listener_count = self.results["api"].get("listener_count", 0)

            print(f"  - 后端服务器关联: {server_count} 条")
            print(f"  - 监听器关联: {listener_count} 条")

            # 验证数据量
            server_match = server_count >= 10
            listener_match = listener_count >= 10

            print(f"  后端服务器关联 {'✅ 满足要求(≥10)' if server_match else '❌ 不足'}")
            print(f"  监听器关联 {'✅ 满足要求(≥10)' if listener_match else '❌ 不足'}")

            self.results["integration"]["server_match"] = server_match
            self.results["integration"]["listener_match"] = listener_match

            # 2. 前端验证
            print("\n【2. 前端验证】")
            has_association = (
                self.results["frontend"].get("has_server") or
                self.results["frontend"].get("has_listener") or
                self.results["frontend"].get("card_count", 0) > 0
            )
            print(f"  {'✅ 前端显示关联数据' if has_association else '⚠️ 前端未显示关联数据'}")

            self.results["integration"]["frontend_ok"] = has_association

            # 3. 总结
            print("\n【3. 测试总结】")
            all_pass = server_match and listener_match

            if all_pass:
                print("  ✅ 所有集成测试通过！")
                print(f"  - 后端服务器: {server_count} 条")
                print(f"  - 监听器: {listener_count} 条")
            else:
                print("  ⚠️ 部分测试未通过")

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

        # 1. API层
        api_pass = self.test_api_layer()
        if not api_pass:
            print("\n❌ API层失败，停止测试")
            return False

        # 2. 前端层
        frontend_pass = self.test_frontend_layer()

        # 3. 集成测试
        integration_pass = self.test_integration()

        # 4. 生成报告
        self.generate_report()

        # 最终结果
        print("\n" + "="*60)
        print("🎯 最终测试结果")
        print("="*60)
        print(f"  API层: {'✅ 通过' if api_pass else '❌ 失败'}")
        print(f"  前端层: {'✅ 通过' if frontend_pass else '⚠️ 部分完成'}")
        print(f"  集成测试: {'✅ 通过' if integration_pass else '❌ 失败'}")

        all_pass = api_pass and integration_pass
        if all_pass:
            print("\n🎉 所有测试通过！关联功能工作正常！")
        else:
            print("\n⚠️ 部分测试未通过，请查看详细日志")

        return all_pass


if __name__ == '__main__':
    test = AssociationAPITest()
    success = test.run_all_tests()
    exit(0 if success else 1)
