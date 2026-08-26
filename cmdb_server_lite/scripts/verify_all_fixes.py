import json
import urllib.request

BASE = "http://127.0.0.1:3000"  # 走前端代理（验证新 dist + 后端全链路）


def children(obj, inst, biz=2):
    url = (f"{BASE}/api/v1/topo/instance/children"
           f"?bk_biz_id={biz}&bk_obj_id={obj}&bk_inst_id={inst}&with_statistics=true")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())['data']


def show(label, data):
    for c in data:
        print(f"  {label} | {c['bk_obj_id']:7s} {c['bk_inst_id']:>8d} {c['bk_inst_name']:14s} "
              f"icon={'首字:'+c['bk_obj_name'][0] if c.get('bk_obj_name') else 'N':8s} "
              f"count={c.get('count',0):>4d} idle={c.get('is_idle_set')} leaf={c.get('is_leaf')}")


print("=== biz2 业务下（应：空闲机池首位 + sys 应用系统）===")
ch = children('biz', 2)
show("biz2", ch)

print("=== biz2: sys(应用系统) -> subsys ===")
sys_node = [c for c in ch if c['bk_obj_id'] == 'sys'][0]
subs = children('sys', sys_node['bk_inst_id'])
show("sys", subs)

print("=== biz2: subsys -> set(演示集群) ===")
sub_node = subs[0]
sets = children('subsys', sub_node['bk_inst_id'])
show("subsys", sets)

print("=== biz2: set -> module ===")
set_node = sets[0]
mods = children('set', set_node['bk_inst_id'])
show("set", mods)

print("=== biz2: 空闲机池 -> 空闲机/故障机 ===")
idle = [c for c in ch if c.get('is_idle_set')][0]
idle_mods = children('set', idle['bk_inst_id'])
show("idle", idle_mods)

print()
print("=== biz3 业务下（应：空闲机池首位 + 1000 sys）===")
ch3 = children('biz', 3, 3)
show("biz3[:3]", ch3[:3])
print(f"  biz3 子节点总数: {len(ch3)}")
