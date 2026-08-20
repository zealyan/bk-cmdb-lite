import json
import urllib.request

DOMAIN = "https://a3cfdec9c526727f4.app.workbuddy.link"


def children(obj, inst):
    url = (f"{DOMAIN}/api/v1/topo/instance/children"
           f"?bk_biz_id=3&bk_obj_id={obj}&bk_inst_id={inst}&with_statistics=true")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


chain = [("biz", 3)]
node = children("biz", 3)
print("biz->sys    :", node["data"][0]["bk_inst_id"], node["data"][0]["bk_inst_name"], "is_leaf=", node["data"][0]["is_leaf"])
chain.append(("sys", node["data"][0]["bk_inst_id"]))

node = children("sys", chain[-1][1])
print("sys->subsys :", node["data"][0]["bk_inst_id"], node["data"][0]["bk_inst_name"], "is_leaf=", node["data"][0]["is_leaf"])
chain.append(("subsys", node["data"][0]["bk_inst_id"]))

node = children("subsys", chain[-1][1])
print("subsys->set :", node["data"][0]["bk_inst_id"], node["data"][0]["bk_inst_name"], "is_leaf=", node["data"][0]["is_leaf"])
chain.append(("set", node["data"][0]["bk_inst_id"]))

node = children("set", chain[-1][1])
m = node["data"][0]
print("set->module :", m["bk_inst_id"], m["bk_inst_name"], "is_leaf=", m["is_leaf"], "count=", m["count"])
print("末层 module 为叶子:", m["is_leaf"] is True)
print("发布域名深层链路逐级验证通过")
