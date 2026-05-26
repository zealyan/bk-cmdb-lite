#!/usr/bin/env python3
"""
完整集成测试脚本
自动处理服务启停，避免DuckDB并发访问问题
"""

import requests
import duckdb
import subprocess
import time
import json
import sys
import os

DB_PATH = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'
API_BASE = 'http://localhost:8000'

def log(message: str, level: str = 'INFO'):
    """记录测试日志"""
    prefix = {
        'INFO': '📋',
        'PASS': '✅',
        'FAIL': '❌',
        'WARN': '⚠️'
    }
    print(f"{prefix.get(level, '📋')} {message}")

def stop_backend_service():
    """停止后端服务"""
    log("停止后端服务...")
    try:
        subprocess.run(['pkill', '-f', 'python3.*main.py'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      timeout=5)
        time.sleep(2)
        log("后端服务已停止", 'PASS')
        return True
    except Exception as e:
        log(f"停止服务失败: {e}", 'FAIL')
        return False

def start_backend_service():
    """启动后端服务"""
    log("启动后端服务...")
    try:
        # 在后台启动服务
        proc = subprocess.Popen(
            ['python3', 'main.py'],
            cwd='/workspace/bk-cmdb/cmdb_server_lite',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)

        # 检查服务是否启动成功
        try:
            response = requests.get(f'{API_BASE}/health', timeout=5)
            if response.status_code == 200:
                log("后端服务已启动", 'PASS')
                return True
        except:
            pass

        log("后端服务启动失败", 'FAIL')
        return False
    except Exception as e:
        log(f"启动服务失败: {e}", 'FAIL')
        return False

def test_database_layer():
    """测试数据库层"""
    log("\n" + "="*60)
    log("【测试1】数据库层测试")
    log("="*60)

    try:
        db = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        log(f"无法连接数据库: {e}", 'FAIL')
        return False

    passed = 0
    failed = 0

    # 1. 检查SLB实例
    log("检查SLB实例表")
    try:
        slbs = db.execute('SELECT COUNT(*) as cnt FROM bk_slb_instances').fetchone()
        log(f"  SLB实例数: {slbs[0]}", 'PASS' if slbs[0] > 0 else 'FAIL')
        if slbs[0] > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 2. 检查后端服务器实例
    log("检查后端服务器实例表")
    try:
        servers = db.execute('SELECT COUNT(*) as cnt FROM bk_slb_server_instances').fetchone()
        log(f"  后端服务器数: {servers[0]}", 'PASS' if servers[0] > 0 else 'FAIL')
        if servers[0] > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 3. 检查监听器实例
    log("检查监听器实例表")
    try:
        listeners = db.execute('SELECT COUNT(*) as cnt FROM bk_slb_listener_instances').fetchone()
        log(f"  监听器数: {listeners[0]}", 'PASS' if listeners[0] > 0 else 'FAIL')
        if listeners[0] > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 4. 检查associations表
    log("检查associations表")
    try:
        total_assocs = db.execute('SELECT COUNT(*) as cnt FROM associations').fetchone()
        log(f"  总关联数: {total_assocs[0]}", 'PASS' if total_assocs[0] > 0 else 'FAIL')
        if total_assocs[0] > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 5. 检查SLB ID=1的关联数据一致性
    log("检查SLB ID=1的关联数据一致性")
    try:
        slb1_assocs = db.execute('''
            SELECT bk_asst_obj_id, COUNT(*) as cnt
            FROM associations
            WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = 1
            GROUP BY bk_asst_obj_id
        ''').fetchall()

        server_assocs = sum([a[1] for a in slb1_assocs if a[0] == 'bk_slb_server'])
        listener_assocs = sum([a[1] for a in slb1_assocs if a[0] == 'bk_slb_listener'])

        # 检查实际实例数
        actual_servers = db.execute('''
            SELECT COUNT(*) FROM bk_slb_server_instances WHERE bk_slb_id = '1'
        ''').fetchone()[0]
        actual_listeners = db.execute('''
            SELECT COUNT(*) FROM bk_slb_listener_instances WHERE bk_slb_id = '1'
        ''').fetchone()[0]

        log(f"  后端服务器关联: {server_assocs}条, 实际实例: {actual_servers}条")
        log(f"  监听器关联: {listener_assocs}条, 实际实例: {actual_listeners}条")

        # 验证一致性
        server_match = server_assocs == actual_servers
        listener_match = listener_assocs == actual_listeners

        if server_match and listener_match:
            log("  ✅ 关联数据一致！", 'PASS')
            passed += 2
        else:
            log("  ❌ 关联数据不一致！", 'FAIL')
            failed += 2
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 2

    # 6. 检查孤立记录
    log("检查是否存在孤立记录")
    try:
        all_assocs = db.execute('''
            SELECT a.id, a.bk_asst_obj_id, a.bk_asst_inst_id
            FROM associations a
            WHERE a.bk_obj_id = 'bk_slb'
        ''').fetchall()

        invalid_count = 0
        for assoc in all_assocs:
            asst_obj = assoc[1]
            asst_id = assoc[2]

            if asst_obj == 'bk_slb_server':
                exists = db.execute('''
                    SELECT COUNT(*) FROM bk_slb_server_instances WHERE id = ?
                ''', [asst_id]).fetchone()[0]
                if not exists:
                    log(f"  ⚠️ 孤立记录: ID={assoc[0]}, 后端服务器ID={asst_id}", 'WARN')
                    invalid_count += 1

            elif asst_obj == 'bk_slb_listener':
                exists = db.execute('''
                    SELECT COUNT(*) FROM bk_slb_listener_instances WHERE id = ?
                ''', [asst_id]).fetchone()[0]
                if not exists:
                    log(f"  ⚠️ 孤立记录: ID={assoc[0]}, 监听器ID={asst_id}", 'WARN')
                    invalid_count += 1

        if invalid_count == 0:
            log("  ✅ 无孤立记录！", 'PASS')
            passed += 1
        else:
            log(f"  ❌ 发现 {invalid_count} 条孤立记录！", 'FAIL')
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    db.close()
    return passed, failed

def test_api_layer():
    """测试API层"""
    log("\n" + "="*60)
    log("【测试2】API层测试")
    log("="*60)

    passed = 0
    failed = 0

    # 1. 测试健康检查
    log("测试健康检查")
    try:
        response = requests.get(f'{API_BASE}/health', timeout=5)
        if response.status_code == 200:
            log(f"  Status: {response.status_code}", 'PASS')
            passed += 1
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1
        return passed, failed

    # 2. 测试获取SLB列表
    log("测试获取SLB列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb/instances', timeout=5)
        data = response.json()
        slb_count = data.get('total', 0)
        log(f"  SLB实例数: {slb_count}", 'PASS' if slb_count > 0 else 'FAIL')
        if slb_count > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 3. 测试获取后端服务器列表
    log("测试获取后端服务器列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb_server/instances', timeout=5)
        data = response.json()
        server_count = data.get('total', 0)
        log(f"  后端服务器数: {server_count}", 'PASS' if server_count > 0 else 'FAIL')
        if server_count > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 4. 测试获取监听器列表
    log("测试获取监听器列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb_listener/instances', timeout=5)
        data = response.json()
        listener_count = data.get('total', 0)
        log(f"  监听器数: {listener_count}", 'PASS' if listener_count > 0 else 'FAIL')
        if listener_count > 0:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    # 5. 测试获取SLB ID=1的关联数据
    log("测试获取SLB ID=1的关联数据")
    try:
        response = requests.get(f'{API_BASE}/api/instances/1/associations', timeout=5)
        data = response.json()
        assocs = data.get('associations', [])

        api_servers = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_server'])
        api_listeners = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_listener'])

        log(f"  后端服务器关联: {api_servers}条", 'PASS' if api_servers >= 10 else 'FAIL')
        log(f"  监听器关联: {api_listeners}条", 'PASS' if api_listeners >= 10 else 'FAIL')

        if api_servers >= 10:
            passed += 1
        else:
            failed += 1

        if api_listeners >= 10:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 2

    # 6. 测试搜索功能
    log("测试搜索功能")
    try:
        response = requests.get(
            f'{API_BASE}/api/models/bk_slb_server/instances',
            params={'search_field': 'bk_slb_id', 'search_value': '1'},
            timeout=5
        )
        data = response.json()
        search_count = data.get('total', 0)
        log(f"  搜索结果: {search_count}条", 'PASS' if search_count >= 10 else 'FAIL')
        if search_count >= 10:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        failed += 1

    return passed, failed

def run_all_tests():
    """运行所有测试"""
    log("\n" + "="*60)
    log("🚀 开始完整集成测试")
    log("="*60)

    total_passed = 0
    total_failed = 0

    # 阶段1: 测试数据库层（需要停止后端服务）
    log("\n📍 阶段1: 数据库层测试")
    if stop_backend_service():
        db_passed, db_failed = test_database_layer()
        total_passed += db_passed
        total_failed += db_failed

        # 阶段2: 测试API层（需要启动后端服务）
        log("\n📍 阶段2: API层测试")
        if start_backend_service():
            api_passed, api_failed = test_api_layer()
            total_passed += api_passed
            total_failed += api_failed
        else:
            log("无法启动后端服务，跳过API层测试", 'FAIL')
            total_failed += 6
    else:
        log("无法停止后端服务，跳过数据库层测试", 'FAIL')
        total_failed += 10

    # 统计结果
    log("\n" + "="*60)
    log("📊 测试结果统计")
    log("="*60)
    log(f"  ✅ 通过: {total_passed}")
    log(f"  ❌ 失败: {total_failed}")
    log(f"  📋 总计: {total_passed + total_failed}")

    # 总结
    if total_failed == 0:
        log("\n🎉 所有测试通过！修复成功！", 'PASS')
        return True
    else:
        log(f"\n⚠️  有 {total_failed} 项测试失败", 'FAIL')
        return False

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
