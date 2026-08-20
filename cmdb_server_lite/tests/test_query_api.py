import requests
import json

# 测试查询接口
url = "http://localhost:8000/find/instassociation"

# 模拟前端查询 - 查询 bk_slb 的关联
test_cases = [
    {
        "name": "查询 bk_slb 的所有关联",
        "params": {
            "bk_obj_id": "bk_slb",
            "condition": {}
        }
    },
    {
        "name": "查询 bk_slb -> bk_slb_server 的关联",
        "params": {
            "bk_obj_id": "bk_slb",
            "condition": {
                "bk_asst_obj_id": "bk_slb_server"
            }
        }
    },
    {
        "name": "查询 bk_slb 的关联（简化版）",
        "params": {
            "condition": {
                "bk_obj_id": "bk_slb"
            }
        }
    }
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"测试: {test['name']}")
    print(f"参数: {json.dumps(test['params'], indent=2)}")
    
    response = requests.post(url, json=test['params'])
    data = response.json()
    
    if 'info' in data:
        print(f"结果: 找到 {len(data['info'])} 条关联记录")
        if data['info']:
            print("  前3条:")
            for item in data['info'][:3]:
                print(f"    - ID:{item.get('id')}, "
                      f"{item.get('bk_obj_id')}:{item.get('bk_inst_id')} -> "
                      f"{item.get('bk_asst_obj_id')}:{item.get('bk_asst_inst_id')}")
    else:
        print(f"错误: {data}")
