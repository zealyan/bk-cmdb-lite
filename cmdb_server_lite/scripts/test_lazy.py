import time, json, urllib.request

B = "http://localhost:5000"


def get(biz, obj, inst, stats=True):
    url = (f"{B}/api/v1/topo/instance/children?bk_biz_id={biz}"
           f"&bk_obj_id={obj}&bk_inst_id={inst}"
           f"&with_statistics={'true' if stats else 'false'}")
    t0 = time.time()
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read().decode())
    t1 = time.time()
    return data, t1 - t0


def show(label, d, dt):
    n = len(d['data'])
    size = len(json.dumps(d).encode())
    f = d['data'][0] if n else {}
    print(f"  {label}: count={n} time={dt*1000:.1f}ms size={size}B "
          f"first={f.get('bk_obj_id')}/{f.get('bk_inst_id')} "
          f"'{f.get('bk_inst_name')}' is_leaf={f.get('is_leaf')}")


d, dt = get(3, 'biz', 3)
show("biz(3)->sys", d, dt)
sys_id = d['data'][0]['bk_inst_id']

d, dt = get(3, 'sys', sys_id)
show("sys->subsys", d, dt)
sub_id = d['data'][0]['bk_inst_id']

d, dt = get(3, 'subsys', sub_id)
show("subsys->set", d, dt)
set_id = d['data'][0]['bk_inst_id']

d, dt = get(3, 'set', set_id)
show("set->module", d, dt)
mod_id = d['data'][0]['bk_inst_id']

d, dt = get(3, 'module', mod_id)
show("module->(叶子，应为空)", d, dt)

# 验证缓存命中：再查一次 biz children，应 <50ms
d, dt = get(3, 'biz', 3)
print(f"  [缓存命中] biz(3)->sys 二次查询: time={dt*1000:.1f}ms count={len(d['data'])}")
