import requests
import json

# 测试查询接口
url = "http://localhost:8000/find/instassociation"

# 模拟前端传递的参数结构
params = {
    "bk_obj_id": "bk_slb",
    "condition": {
        "bk_asst_id": "to",
        "bk_obj_asst_id": "bk_slb_to_bk_slb_listener",
        "bk_inst_id": 8,
        "bk_asst_obj_id": "bk_slb_listener"
    }
}

response = requests.post(url, json=params)
data = response.json()

print("Query parameters:")
print(json.dumps(params, indent=2))
print("\n" + "="*50)
print(f"Found {len(data.get('info', []))} associations")
print("\nFirst 5 associations:")
for item in data.get('info', [])[:5]:
    print(f"  - ID: {item.get('id')}, Instance {item.get('bk_inst_id')} -> {item.get('bk_asst_obj_id')}:{item.get('bk_asst_inst_id')}")
