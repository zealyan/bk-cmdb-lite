import time, json, sys, os
os.chdir('/workspace/bk-cmdb-lite/cmdb_server_lite')
sys.path.insert(0, '/workspace/bk-cmdb-lite/cmdb_server_lite')
from app.service import topo_service

def count(n):
    c = 1
    for ch in n.children:
        c += count(ch)
    return c

for ws in (False, True):
    print(f"\n=== with_statistics={ws} ===")
    t0 = time.time()
    tree = topo_service.get_mainline_instance_topo(bk_biz_id=3, with_detail=False, with_statistics=ws)
    t1 = time.time()
    print("节点总数:", count(tree))
    print("计算(建树+统计)耗时: %.2fs" % (t1 - t0))
    t2 = time.time()
    d = tree.to_dict(with_statistics=ws)
    t3 = time.time()
    print("to_dict 耗时: %.2fs" % (t3 - t2))
    t4 = time.time()
    s = json.dumps(d, ensure_ascii=False)
    t5 = time.time()
    print("json.dumps 耗时: %.2fs" % (t5 - t4))
    print("JSON 大小: %.1f MB" % (len(s.encode('utf-8')) / 1024 / 1024))
    print("总计: %.2fs" % (t5 - t0))
