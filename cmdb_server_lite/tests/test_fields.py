import requests
import json

# 测试查询接口并查看返回的字段
url = "http://localhost:8000/find/instassociation"

params = {
    "bk_obj_id": "bk_slb",
    "condition": {
        "bk_asst_obj_id": "bk_slb_server"
    }
}

print("发送查询请求...")
response = requests.post(url, json=params)
data = response.json()

if 'info' in data and len(data['info']) > 0:
    print(f"\n查询成功，返回 {len(data['info'])} 条记录")
    print("\n第一条记录的字段：")
    first_record = data['info'][0]
    for key, value in first_record.items():
        print(f"  {key}: {value} (type: {type(value).__name__})")
    
    print("\n\n完整的JSON:")
    print(json.dumps(first_record, indent=2))
else:
    print("查询失败:", data)
