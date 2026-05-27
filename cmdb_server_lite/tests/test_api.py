import requests
import json

# 查询模型关联
response = requests.post('http://localhost:8000/find/objectassociation', json={'condition': {'bk_obj_id': 'bk_slb'}})
print("=== /find/objectassociation ===")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

# 查询关联类型
response2 = requests.post('http://localhost:8000/find/associationtype', json={})
print("\n=== /find/associationtype ===")
print(f"Status: {response2.status_code}")
print(f"Response: {json.dumps(response2.json(), indent=2, ensure_ascii=False)}")
