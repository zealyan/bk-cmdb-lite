#!/usr/bin/env python3
"""
完整集成测试脚本
验证数据库层、API层和前端层的数据一致性
"""

import requests
import duckdb
import json
from typing import Dict, List, Any

DB_PATH = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'
API_BASE = 'http://localhost:8000'

class IntegrationTester:
    def __init__(self):
        self.db = duckdb.connect(DB_PATH)
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def log(self, message: str, level: str = 'INFO'):
        """记录测试日志"""
        prefix = {
            'INFO': '📋',
            'PASS': '✅',
            'FAIL': '❌',
            'WARN': '⚠️'
        }
        print(f"{prefix.get(level, '📋')} {message}")

    def test_database_layer(self):
        """测试数据库层"""
        self.log("\n" + "="*60)
        self.log("【测试1】数据库层测试")
        self.log("="*60)

        # 1. 检查SLB实例
        self.log("检查SLB实例表")
        slbs = self.db.execute('SELECT COUNT(*) as cnt FROM bk_slb_instances').fetchone()
        self.test_results.append({
            'layer': 'database',
            'test': 'slb_count',
            'expected': '> 0',
            'actual': slbs[0]
        })
        self.log(f"  SLB实例数: {slbs[0]}", 'PASS' if slbs[0] > 0 else 'FAIL')

        # 2. 检查后端服务器实例
        self.log("检查后端服务器实例表")
        servers = self.db.execute('SELECT COUNT(*) as cnt FROM bk_slb_server_instances').fetchone()
        self.test_results.append({
            'layer': 'database',
            'test': 'server_count',
            'expected': '> 0',
            'actual': servers[0]
        })
        self.log(f"  后端服务器数: {servers[0]}", 'PASS' if servers[0] > 0 else 'FAIL')

        # 3. 检查监听器实例
        self.log("检查监听器实例表")
        listeners = self.db.execute('SELECT COUNT(*) as cnt FROM bk_slb_listener_instances').fetchone()
        self.test_results.append({
            'layer': 'database',
            'test': 'listener_count',
            'expected': '> 0',
            'actual': listeners[0]
        })
        self.log(f"  监听器数: {listeners[0]}", 'PASS' if listeners[0] > 0 else 'FAIL')

        # 4. 检查associations表
        self.log("检查associations表")
        total_assocs = self.db.execute('SELECT COUNT(*) as cnt FROM associations').fetchone()
        self.test_results.append({
            'layer': 'database',
            'test': 'associations_count',
            'expected': '> 0',
            'actual': total_assocs[0]
        })
        self.log(f"  总关联数: {total_assocs[0]}", 'PASS' if total_assocs[0] > 0 else 'FAIL')

        # 5. 检查SLB ID=1的关联数据
        self.log("检查SLB ID=1的关联数据一致性")
        slb1_assocs = self.db.execute('''
            SELECT bk_asst_obj_id, COUNT(*) as cnt
            FROM associations
            WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = 1
            GROUP BY bk_asst_obj_id
        ''').fetchall()

        server_assocs = sum([a[1] for a in slb1_assocs if a[0] == 'bk_slb_server'])
        listener_assocs = sum([a[1] for a in slb1_assocs if a[0] == 'bk_slb_listener'])

        # 检查实际实例数
        actual_servers = self.db.execute('''
            SELECT COUNT(*) FROM bk_slb_server_instances WHERE bk_slb_id = '1'
        ''').fetchone()[0]
        actual_listeners = self.db.execute('''
            SELECT COUNT(*) FROM bk_slb_listener_instances WHERE bk_slb_id = '1'
        ''').fetchone()[0]

        self.log(f"  后端服务器关联: {server_assocs}条, 实际实例: {actual_servers}条")
        self.log(f"  监听器关联: {listener_assocs}条, 实际实例: {actual_listeners}条")

        # 验证一致性
        server_match = server_assocs == actual_servers
        listener_match = listener_assocs == actual_listeners

        self.test_results.append({
            'layer': 'database',
            'test': 'slb1_server_association_consistency',
            'expected': actual_servers,
            'actual': server_assocs
        })
        self.test_results.append({
            'layer': 'database',
            'test': 'slb1_listener_association_consistency',
            'expected': actual_listeners,
            'actual': listener_assocs
        })

        if server_match and listener_match:
            self.log("  ✅ 关联数据一致！", 'PASS')
            self.passed += 2
        else:
            self.log("  ❌ 关联数据不一致！", 'FAIL')
            self.failed += 2

        # 6. 检查孤立记录
        self.log("检查是否存在孤立记录")
        all_assocs = self.db.execute('''
            SELECT a.id, a.bk_asst_obj_id, a.bk_asst_inst_id
            FROM associations a
            WHERE a.bk_obj_id = 'bk_slb'
        ''').fetchall()

        invalid_count = 0
        for assoc in all_assocs:
            asst_obj = assoc[1]
            asst_id = assoc[2]

            if asst_obj == 'bk_slb_server':
                exists = self.db.execute('''
                    SELECT COUNT(*) FROM bk_slb_server_instances WHERE id = ?
                ''', [asst_id]).fetchone()[0]
                if not exists:
                    self.log(f"  ⚠️ 孤立记录: ID={assoc[0]}, 后端服务器ID={asst_id}", 'WARN')
                    invalid_count += 1

            elif asst_obj == 'bk_slb_listener':
                exists = self.db.execute('''
                    SELECT COUNT(*) FROM bk_slb_listener_instances WHERE id = ?
                ''', [asst_id]).fetchone()[0]
                if not exists:
                    self.log(f"  ⚠️ 孤立记录: ID={assoc[0]}, 监听器ID={asst_id}", 'WARN')
                    invalid_count += 1

        if invalid_count == 0:
            self.log("  ✅ 无孤立记录！", 'PASS')
            self.passed += 1
        else:
            self.log(f"  ❌ 发现 {invalid_count} 条孤立记录！", 'FAIL')
            self.failed += 1

    def test_api_layer(self):
        """测试API层"""
        self.log("\n" + "="*60)
        self.log("【测试2】API层测试")
        self.log("="*60)

        # 1. 测试健康检查
        self.log("测试健康检查")
        try:
            response = requests.get(f'{API_BASE}/health', timeout=5)
            health_ok = response.status_code == 200
            self.test_results.append({
                'layer': 'api',
                'test': 'health_check',
                'expected': 200,
                'actual': response.status_code
            })
            self.log(f"  Status: {response.status_code}", 'PASS' if health_ok else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')
            self.failed += 1
            return

        # 2. 测试获取SLB列表
        self.log("测试获取SLB列表")
        try:
            response = requests.get(f'{API_BASE}/api/models/bk_slb/instances', timeout=5)
            data = response.json()
            slb_count = data.get('total', 0)
            self.test_results.append({
                'layer': 'api',
                'test': 'slb_list',
                'expected': '> 0',
                'actual': slb_count
            })
            self.log(f"  SLB实例数: {slb_count}", 'PASS' if slb_count > 0 else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')

        # 3. 测试获取后端服务器列表
        self.log("测试获取后端服务器列表")
        try:
            response = requests.get(f'{API_BASE}/api/models/bk_slb_server/instances', timeout=5)
            data = response.json()
            server_count = data.get('total', 0)
            self.test_results.append({
                'layer': 'api',
                'test': 'server_list',
                'expected': '> 0',
                'actual': server_count
            })
            self.log(f"  后端服务器数: {server_count}", 'PASS' if server_count > 0 else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')

        # 4. 测试获取监听器列表
        self.log("测试获取监听器列表")
        try:
            response = requests.get(f'{API_BASE}/api/models/bk_slb_listener/instances', timeout=5)
            data = response.json()
            listener_count = data.get('total', 0)
            self.test_results.append({
                'layer': 'api',
                'test': 'listener_list',
                'expected': '> 0',
                'actual': listener_count
            })
            self.log(f"  监听器数: {listener_count}", 'PASS' if listener_count > 0 else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')

        # 5. 测试获取SLB ID=1的关联数据
        self.log("测试获取SLB ID=1的关联数据")
        try:
            response = requests.get(f'{API_BASE}/api/instances/1/associations', timeout=5)
            data = response.json()
            assocs = data.get('associations', [])

            api_servers = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_server'])
            api_listeners = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_listener'])

            self.test_results.append({
                'layer': 'api',
                'test': 'slb1_server_associations',
                'expected': '>= 10',
                'actual': api_servers
            })
            self.test_results.append({
                'layer': 'api',
                'test': 'slb1_listener_associations',
                'expected': '>= 10',
                'actual': api_listeners
            })

            self.log(f"  后端服务器关联: {api_servers}条", 'PASS' if api_servers >= 10 else 'FAIL')
            self.log(f"  监听器关联: {api_listeners}条", 'PASS' if api_listeners >= 10 else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')

        # 6. 测试搜索功能
        self.log("测试搜索功能")
        try:
            response = requests.get(
                f'{API_BASE}/api/models/bk_slb_server/instances',
                params={'search_field': 'bk_slb_id', 'search_value': '1'},
                timeout=5
            )
            data = response.json()
            search_count = data.get('total', 0)
            self.test_results.append({
                'layer': 'api',
                'test': 'search_servers_by_slb_id',
                'expected': '>= 10',
                'actual': search_count
            })
            self.log(f"  搜索结果: {search_count}条", 'PASS' if search_count >= 10 else 'FAIL')
        except Exception as e:
            self.log(f"  Error: {e}", 'FAIL')

    def test_data_consistency(self):
        """测试数据一致性"""
        self.log("\n" + "="*60)
        self.log("【测试3】数据一致性测试")
        self.log("="*60)

        # 获取数据库数据
        db_slb_count = self.db.execute('SELECT COUNT(*) FROM bk_slb_instances').fetchone()[0]
        db_server_count = self.db.execute('SELECT COUNT(*) FROM bk_slb_server_instances').fetchone()[0]
        db_listener_count = self.db.execute('SELECT COUNT(*) FROM bk_slb_listener_instances').fetchone()[0]

        # 获取API数据
        api_slb = requests.get(f'{API_BASE}/api/models/bk_slb/instances', timeout=5).json()
        api_server = requests.get(f'{API_BASE}/api/models/bk_slb_server/instances', timeout=5).json()
        api_listener = requests.get(f'{API_BASE}/api/models/bk_slb_listener/instances', timeout=5).json()

        api_slb_count = api_slb.get('total', 0)
        api_server_count = api_server.get('total', 0)
        api_listener_count = api_listener.get('total', 0)

        # 验证一致性
        self.log("数据库 vs API 数据对比:")

        slb_match = db_slb_count == api_slb_count
        server_match = db_server_count == api_server_count
        listener_match = db_listener_count == api_listener_count

        self.log(f"  SLB实例: DB={db_slb_count}, API={api_slb_count}",
                 'PASS' if slb_match else 'FAIL')
        self.log(f"  后端服务器: DB={db_server_count}, API={api_server_count}",
                 'PASS' if server_match else 'FAIL')
        self.log(f"  监听器: DB={db_listener_count}, API={api_listener_count}",
                 'PASS' if listener_match else 'FAIL')

        self.test_results.append({
            'layer': 'consistency',
            'test': 'slb_consistency',
            'expected': db_slb_count,
            'actual': api_slb_count
        })
        self.test_results.append({
            'layer': 'consistency',
            'test': 'server_consistency',
            'expected': db_server_count,
            'actual': api_server_count
        })
        self.test_results.append({
            'layer': 'consistency',
            'test': 'listener_consistency',
            'expected': db_listener_count,
            'actual': api_listener_count
        })

        if slb_match and server_match and listener_match:
            self.log("\n✅ 所有数据层一致！", 'PASS')
            self.passed += 3
        else:
            self.log("\n❌ 数据层不一致！", 'FAIL')
            self.failed += 3

        # 测试关联数据一致性
        self.log("\n测试关联数据一致性:")

        # 数据库中的SLB ID=1关联
        db_slb1_assocs = self.db.execute('''
            SELECT bk_asst_obj_id, COUNT(*) as cnt
            FROM associations
            WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = 1
            GROUP BY bk_asst_obj_id
        ''').fetchall()

        db_servers = sum([a[1] for a in db_slb1_assocs if a[0] == 'bk_slb_server'])
        db_listeners = sum([a[1] for a in db_slb1_assocs if a[0] == 'bk_slb_listener'])

        # API中的SLB ID=1关联
        api_slb1 = requests.get(f'{API_BASE}/api/instances/1/associations', timeout=5).json()
        api_assocs = api_slb1.get('associations', [])
        api_servers = len([a for a in api_assocs if a.get('bk_asst_obj_id') == 'bk_slb_server'])
        api_listeners = len([a for a in api_assocs if a.get('bk_asst_obj_id') == 'bk_slb_listener'])

        server_assoc_match = db_servers == api_servers
        listener_assoc_match = db_listeners == api_listeners

        self.log(f"  后端服务器关联: DB={db_servers}, API={api_servers}",
                 'PASS' if server_assoc_match else 'FAIL')
        self.log(f"  监听器关联: DB={db_listeners}, API={api_listeners}",
                 'PASS' if listener_assoc_match else 'FAIL')

        self.test_results.append({
            'layer': 'consistency',
            'test': 'slb1_server_association_consistency',
            'expected': db_servers,
            'actual': api_servers
        })
        self.test_results.append({
            'layer': 'consistency',
            'test': 'slb1_listener_association_consistency',
            'expected': db_listeners,
            'actual': api_listeners
        })

        if server_assoc_match and listener_assoc_match:
            self.log("\n✅ 关联数据一致！", 'PASS')
            self.passed += 2
        else:
            self.log("\n❌ 关联数据不一致！", 'FAIL')
            self.failed += 2

    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*60)
        self.log("🚀 开始完整集成测试")
        self.log("="*60)

        self.test_database_layer()
        self.test_api_layer()
        self.test_data_consistency()

        # 统计结果
        self.log("\n" + "="*60)
        self.log("📊 测试结果统计")
        self.log("="*60)
        self.log(f"  ✅ 通过: {self.passed}")
        self.log(f"  ❌ 失败: {self.failed}")
        self.log(f"  📋 总计: {self.passed + self.failed}")

        # 保存测试结果
        with open('/tmp/test_results.json', 'w') as f:
            json.dump({
                'passed': self.passed,
                'failed': self.failed,
                'total': self.passed + self.failed,
                'results': self.test_results
            }, f, indent=2)

        self.log("\n测试结果已保存到: /tmp/test_results.json")

        # 总结
        if self.failed == 0:
            self.log("\n🎉 所有测试通过！修复成功！", 'PASS')
            return True
        else:
            self.log(f"\n⚠️  有 {self.failed} 项测试失败", 'FAIL')
            return False

    def close(self):
        """关闭数据库连接"""
        self.db.close()

if __name__ == '__main__':
    tester = IntegrationTester()
    success = tester.run_all_tests()
    tester.close()

    exit(0 if success else 1)
