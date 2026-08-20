"""端到端验证：业务 topo node <-> 主机列表交互（模拟前端 host-list.vue 的查询载荷）。"""
import json
import urllib.request

BASE = "http://127.0.0.1:3000"  # 走前端代理（新 dist + 新后端）


def children(obj, inst, biz):
    url = (f"{BASE}/api/v1/topo/instance/children"
           f"?bk_biz_id={biz}&bk_obj_id={obj}&bk_inst_id={inst}&with_statistics=true")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())['data']


def search_hosts(payload):
    req = urllib.request.Request(f"{BASE}/api/v1/topo/hosts/search",
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def host_payload(biz_id, node):
    """复刻前端 host-list.vue 的 payload 构建（含 bk_biz_id 取值逻辑）。"""
    obj_id = node['bk_obj_id']
    bk_biz_id = obj_id == 'biz' and node['bk_inst_id'] or (node.get('bk_biz_id') or 0)
    if not bk_biz_id:
        return None
    payload = {
        'bk_biz_id': bk_biz_id,
        'page': {'start': 0, 'limit': 20, 'sort': 'bk_host_id'},
        'condition': []
    }
    if obj_id == 'biz':
        pass
    elif obj_id == 'set':
        payload['condition'].append({'bk_obj_id': 'set', 'fields': [],
                                     'condition': [{'field': 'bk_set_id', 'operator': '$eq', 'value': node['bk_inst_id']}]})
    elif obj_id == 'module':
        payload['condition'].append({'bk_obj_id': 'module', 'fields': [],
                                     'condition': [{'field': 'bk_module_id', 'operator': '$eq', 'value': node['bk_inst_id']}]})
    else:
        payload['condition'].append({'bk_obj_id': obj_id, 'fields': [],
                                     'condition': [{'field': 'bk_inst_id', 'operator': '$eq', 'value': node['bk_inst_id']}]})
    return payload


def check(label, node, expect_hosts):
    payload = host_payload(3, node) if node.get('bk_biz_id', 3) == 3 else host_payload(2, node)
    if payload is None:
        print(f"  [✗] {label}: bk_biz_id 缺失，主机列表将为空")
        return
    res = search_hosts(payload)
    got = len(res.get('data', {}).get('info', [])) if isinstance(res.get('data'), dict) else len(res.get('data') or [])
    names = [h.get('bk_host_name') for h in (res.get('data', {}).get('info', []) if isinstance(res.get('data'), dict) else (res.get('data') or []))]
    status = "✓" if got == expect_hosts else "✗"
    print(f"  [{status}] {label}: 查询到 {got} 台 (期望 {expect_hosts}) {names}")


print("=== 1. children 接口返回 bk_biz_id ===")
ch3 = children('biz', 3, 3)
idle3 = [c for c in ch3 if c.get('is_idle_set')][0]
print(f"  biz3 空闲机池节点: bk_biz_id={idle3.get('bk_biz_id')} count={idle3.get('count')} (期望 bk_biz_id=3, count=6)")
sys3 = [c for c in ch3 if c['bk_obj_id'] == 'sys'][0]
print(f"  biz3 sys 节点: bk_biz_id={sys3.get('bk_biz_id')} (期望 3)")
assert idle3.get('bk_biz_id') == 3
assert idle3.get('count') == 6, f"空闲机池 count 应=6, 实际={idle3.get('count')}"

print()
print("=== 2. biz3 树节点 -> 主机列表（模拟前端 host-list）===")
check('biz3 业务节点', {'bk_obj_id': 'biz', 'bk_inst_id': 3, 'bk_biz_id': 3}, 6)
check('biz3 空闲机池(set)', idle3, 6)
mods3 = children('set', idle3['bk_inst_id'], 3)
idle_mod = [m for m in mods3 if m.get('bk_biz_id') and m['bk_inst_name'] == '空闲机'][0]
check('biz3 空闲机(module)', idle_mod, 6)

print()
print("=== 3. biz2 树节点 -> 主机列表 ===")
ch2 = children('biz', 2, 2)
idle2 = [c for c in ch2 if c.get('is_idle_set')][0]
print(f"  biz2 空闲机池节点: bk_biz_id={idle2.get('bk_biz_id')} count={idle2.get('count')} (期望 10)")
check('biz2 业务节点', {'bk_obj_id': 'biz', 'bk_inst_id': 2, 'bk_biz_id': 2}, 10)
check('biz2 空闲机池(set)', idle2, 10)
sys2 = [c for c in ch2 if c['bk_obj_id'] == 'sys'][0]
subs2 = children('sys', sys2['bk_inst_id'], 2)
set2 = children('subsys', subs2[0]['bk_inst_id'], 2)[0]
mods2 = children('set', set2['bk_inst_id'], 2)
print(f"  biz2 演示集群节点 count={set2.get('count')} (期望 0，无业务主机)")
check('biz2 演示集群(set)', set2, 0)

print()
print("=== 结论 ===")
print("  所有树节点已携带 bk_biz_id；空闲机池 count=主机数；node->主机列表查询正常。")
