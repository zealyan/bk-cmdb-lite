# CMDB Server Lite API 文档

## 基于 main.py 分析

### API 端点总览

| HTTP方法 | 路径 | 功能描述 |
|---------|------|----------|
| GET | `/` | 根路径欢迎信息 |
| GET | `/health` | 健康检查 |
| GET | `/api/classifications` | 获取所有分类列表 |
| POST | `/api/find/classificationobject` | 查询分类及其下属模型 |
| GET | `/api/classifications/{classification_id}` | 获取单个分类详情 |
| GET | `/api/classifications/{classification_id}/models` | 获取分类下的所有模型 |
| GET | `/api/models` | 获取所有模型列表 |
| GET | `/api/models/{model_id}` | 获取单个模型详情 |
| GET | `/api/models/{model_id}/attributes` | 获取模型属性列表 |
| POST | `/find/associationtype` | 查询关联类型 |
| POST | `/find/objectassociation` | 查询对象关联 |
| POST | `/find/{obj_id}` | 根据模型ID查询实例详情 |
| GET | `/api/models/{model_id}/associations` | 获取模型的关联关系 |
| GET | `/api/models/{model_id}/instances` | 获取模型实例列表（分页） |
| POST | `/api/models/{model_id}/instances/search` | 高级搜索模型实例 |
| GET | `/api/models/{model_id}/instances/{instance_id}` | 获取单个实例详情 |
| GET | `/api/instances/{instance_id}/associations` | 获取实例的关联关系 |
| POST | `/create/instassociation` | 创建实例关联 |
| DELETE | `/delete/instassociation/{obj_id}/{inst_asst_id}` | 删除实例关联 |
| POST | `/find/instassociation` | 查询实例关联 |
| GET | `/api/instances/{instance_id}/related` | 获取实例的相关实例 |
| GET | `/api/relations` | 获取所有关系类型 |
| GET | `/api/statistics` | 获取统计数据 |
| POST | `/api/usercustom/user/search` | 获取用户配置 |
| POST | `/api/usercustom` | 保存用户配置 |
| GET | `/api/users` | 获取用户列表 |
| GET | `/api/usercustom/model/{obj_id}` | 获取模型的列配置 |
| POST | `/api/usercustom/model/{obj_id}` | 保存模型的列配置 |
| POST | `/api/models/{model_id}/instances/check-associations` | 检查实例关联数量 |
| POST | `/api/models/{model_id}/instances` | 创建新的模型实例 |
| PUT | `/api/models/{model_id}/instances/{instance_id}` | 更新单个实例 |
| PUT | `/api/models/{model_id}/instances` | 批量更新实例 |
| DELETE | `/api/models/{model_id}/instances` | 删除实例（支持批量） |

---

## 详细 API 文档

### 1. 根路径

**GET /**

返回欢迎信息

**响应示例:**
```json
{
  "message": "CMDB Server Lite API",
  "version": "1.0.0"
}
```

---

### 2. 健康检查

**GET /health**

检查服务健康状态和数据库连接

**响应示例:**
```json
{
  "status": "healthy",
  "service": "CMDB Server Lite",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "path": "/workspace/cmdb_server_lite/cmdb.duckdb"
  },
  "cors": {
    "allow_origins": ["*"],
    "allow_credentials": true,
    "allow_methods": ["*"],
    "allow_headers": ["*"]
  }
}
```

---

### 3. 获取所有分类

**GET /api/classifications**

获取所有分类列表

**响应示例:**
```json
{
  "classifications": [
    {
      "id": 1,
      "bk_classification_id": "bk_host",
      "bk_classification_name": "主机",
      "bk_parent_id": null,
      "bk_ishidden": false,
      "create_time": "2024-01-01 00:00:00"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjClassification ORDER BY id
```

---

### 4. 查询分类及其下属模型

**POST /api/find/classificationobject**

查询分类及其下属模型信息，对应原项目的 searchClassificationsObjects API

**请求体:**
```json
{}
```

**响应示例:**
```json
[
  {
    "id": 1,
    "bk_classification_id": "bk_host",
    "bk_classification_name": "主机",
    "bk_objects": [
      {
        "bk_obj_id": "bk_host",
        "bk_obj_name": "主机",
        "bk_classification_id": "bk_host",
        "bk_ispaused": false,
        "bk_ishidden": false
      }
    ]
  }
]
```

**SQL 查询:**
```sql
-- 获取分类
SELECT * FROM cc_ObjClassification 
WHERE bk_ishidden = FALSE OR bk_ishidden IS NULL
ORDER BY id

-- 获取分类下的模型
SELECT * FROM cc_ObjDes 
WHERE bk_classification_id = ? 
AND (bk_ispaused = FALSE OR bk_ispaused IS NULL)
AND (bk_ishidden = FALSE OR bk_ishidden IS NULL)
ORDER BY obj_sort_number, bk_obj_id
```

---

### 5. 获取单个分类详情

**GET /api/classifications/{classification_id}**

**路径参数:**
- `classification_id` (string) - 分类ID

**响应示例:**
```json
{
  "classification": {
    "id": 1,
    "bk_classification_id": "bk_host",
    "bk_classification_name": "主机"
  }
}
```

**错误响应:**
```json
{
  "detail": "Classification not found"
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjClassification WHERE bk_classification_id = ?
```

---

### 6. 获取分类下的模型

**GET /api/classifications/{classification_id}/models**

**路径参数:**
- `classification_id` (string) - 分类ID

**响应示例:**
```json
{
  "models": [
    {
      "bk_obj_id": "bk_host",
      "bk_obj_name": "主机",
      "bk_classification_id": "bk_host"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjDes WHERE bk_classification_id = ? ORDER BY obj_sort_number
```

---

### 7. 获取所有模型

**GET /api/models**

**响应示例:**
```json
{
  "models": [
    {
      "bk_obj_id": "bk_host",
      "bk_obj_name": "主机",
      "bk_classification_id": "bk_host"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjDes
```

---

### 8. 获取单个模型详情

**GET /api/models/{model_id}**

**路径参数:**
- `model_id` (string) - 模型ID

**响应示例:**
```json
{
  "model": {
    "bk_obj_id": "bk_host",
    "bk_obj_name": "主机",
    "bk_classification_id": "bk_host"
  }
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjDes WHERE bk_obj_id = ?
```

---

### 9. 获取模型属性

**GET /api/models/{model_id}/attributes**

**路径参数:**
- `model_id` (string) - 模型ID

**响应示例:**
```json
{
  "attributes": [
    {
      "bk_property_id": "bk_host_name",
      "bk_property_name": "主机名称",
      "bk_property_type": "singlechar",
      "isrequired": true,
      "option": null,
      "bk_property_option": null
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_ObjAttDes WHERE bk_obj_id = ? ORDER BY bk_property_index
```

---

### 10. 查询关联类型

**POST /find/associationtype**

**请求体:**
```json
{}
```

**响应示例:**
```json
{
  "info": [
    {
      "bk_asst_id": "bk_relation",
      "bk_asst_name": "关联关系",
      "src_des": "源描述",
      "dest_des": "目标描述",
      "direction": "forward"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_AsstDes
```

---

### 11. 查询对象关联

**POST /find/objectassociation**

**请求体:**
```json
{
  "condition": {
    "bk_obj_id": "bk_host",
    "bk_asst_obj_id": "bk_slb"
  }
}
```

**响应示例:**
```json
[
  {
    "bk_obj_id": "bk_host",
    "target_obj_id": "bk_slb",
    "target_obj_name": "负载均衡",
    "bk_asst_id": "bk_relation",
    "bk_asst_name": "关联关系",
    "cardinality": "1:N",
    "direction": "forward"
  }
]
```

**SQL 查询:**
```sql
SELECT 
    oa.*,
    ad.bk_asst_name,
    ad.src_des,
    ad.dest_des,
    ad.direction
FROM cc_ObjAsst oa
JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
[WHERE conditions]
```

---

### 12. 根据模型ID查询实例

**POST /find/{obj_id}**

**路径参数:**
- `obj_id` (string) - 模型ID

**请求体:**
```json
{
  "condition": {
    "bk_obj_id": "bk_host",
    "id": 123
  }
}
```

**响应示例:**
```json
{
  "id": 123,
  "bk_host_name": "host-001",
  "bk_os_type": "Linux",
  "create_time": "2024-01-01 00:00:00"
}
```

**SQL 查询:**
```sql
SELECT * FROM "cc_ObjectBase_0_pub_{obj_id}"
[WHERE conditions]
LIMIT 1
```

---

### 13. 获取模型的关联关系

**GET /api/models/{model_id}/associations**

**路径参数:**
- `model_id` (string) - 模型ID

**响应示例:**
```json
{
  "associations": [
    {
      "bk_obj_id": "bk_host",
      "target_obj_id": "bk_slb",
      "relation_type_id": "bk_relation",
      "relation_type_name": "关联关系",
      "cardinality": "1:N",
      "direction": "forward"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT 
    oa.bk_obj_id,
    oa.target_obj_id,
    oa.target_obj_name,
    oa.bk_asst_id AS relation_type_id,
    ad.bk_asst_name AS relation_type_name,
    oa.cardinality,
    ad.direction
FROM cc_ObjAsst oa
JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
WHERE oa.bk_obj_id = ?
```

---

### 14. 获取模型实例列表（分页）

**GET /api/models/{model_id}/instances**

**路径参数:**
- `model_id` (string) - 模型ID

**查询参数:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量（最大1000） |
| search | string | None | 搜索关键词 |
| search_field | string | None | 搜索字段 |
| search_value | string | None | 搜索值 |
| fuzzy | bool | False | 是否模糊匹配 |
| sort | string | None | 排序字段 |
| order | string | asc | 排序方向 |

**响应示例:**
```json
{
  "instances": [
    {
      "id": 1,
      "bk_host_name": "host-001",
      "bk_os_type": "Linux"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

**SQL 查询:**
```sql
SELECT * FROM "cc_ObjectBase_0_pub_{model_id}"
[WHERE conditions]
[ORDER BY sort_field]
LIMIT {page_size} OFFSET {offset}
```

---

### 15. 高级搜索模型实例

**POST /api/models/{model_id}/instances/search**

**请求体:**
```json
{
  "page": 1,
  "page_size": 20,
  "search": "keyword",
  "search_field": "bk_host_name",
  "search_value": "host",
  "fuzzy": true,
  "sort": "bk_host_name",
  "order": "asc",
  "conditions": [
    {"field": "bk_os_type", "operator": "$eq", "value": "Linux"},
    {"field": "cpu", "operator": "$gt", "value": "4"}
  ]
}
```

**支持的操作符:**
| 操作符 | 说明 |
|--------|------|
| $eq | 等于 |
| $ne | 不等于 |
| $in | 在数组中 |
| $nin | 不在数组中 |
| $gt | 大于 |
| $lt | 小于 |
| $gte | 大于等于 |
| $lte | 小于等于 |
| $like / $regex | 模糊匹配 |

**响应示例:**
```json
{
  "instances": [...],
  "page": 1,
  "page_size": 20,
  "total": 50
}
```

---

### 16. 获取单个实例详情

**GET /api/models/{model_id}/instances/{instance_id}**

**路径参数:**
- `model_id` (string) - 模型ID
- `instance_id` (int) - 实例ID

**响应示例:**
```json
{
  "instance": {
    "id": 1,
    "bk_host_name": "host-001",
    "bk_os_type": "Linux",
    "create_time": "2024-01-01 00:00:00"
  }
}
```

**SQL 查询:**
```sql
SELECT * FROM "cc_ObjectBase_0_pub_{model_id}" WHERE id = {instance_id}
```

---

### 17. 获取实例的关联关系

**GET /api/instances/{instance_id}/associations**

**路径参数:**
- `instance_id` (int) - 实例ID

**响应示例:**
```json
{
  "associations": [
    {
      "bk_inst_id": 1,
      "bk_asst_inst_id": 100,
      "bk_obj_asst_id": "association-001",
      "bk_relation_type_id": "bk_relation"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_InstAsst_0_pub WHERE bk_inst_id = ? OR bk_asst_inst_id = ?
```

---

### 18. 创建实例关联

**POST /create/instassociation**

**请求体:**
```json
{
  "bk_obj_id": "bk_host",
  "bk_inst_id": 1,
  "bk_asst_obj_id": "bk_slb",
  "bk_asst_inst_id": 100,
  "bk_obj_asst_id": "association-001",
  "bk_relation_type_id": "bk_relation"
}
```

**响应示例:**
```json
{
  "id": 1001,
  "result": true
}
```

**SQL 查询:**
```sql
INSERT INTO cc_InstAsst_0_pub
(_id, id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
```

---

### 19. 删除实例关联

**DELETE /delete/instassociation/{obj_id}/{inst_asst_id}**

**路径参数:**
- `obj_id` (string) - 模型ID
- `inst_asst_id` (int) - 关联ID

**响应示例:**
```json
{
  "result": true,
  "deleted": 1
}
```

**SQL 查询:**
```sql
DELETE FROM cc_InstAsst_0_pub WHERE id = ?
```

---

### 20. 查询实例关联

**POST /find/instassociation**

**请求体:**
```json
{
  "bk_obj_id": "bk_host",
  "condition": {
    "bk_inst_id": 1,
    "bk_asst_obj_id": "bk_slb"
  }
}
```

**响应示例:**
```json
{
  "info": [
    {
      "bk_obj_id": "bk_host",
      "bk_inst_id": 1,
      "bk_asst_obj_id": "bk_slb",
      "bk_asst_inst_id": 100
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM cc_InstAsst_0_pub
[WHERE conditions]
```

---

### 21. 获取实例的相关实例

**GET /api/instances/{instance_id}/related**

**路径参数:**
- `instance_id` (int) - 实例ID

**查询参数:**
- `model_id` (string, optional) - 模型ID过滤

**响应示例:**
```json
{
  "related": [
    {
      "bk_inst_id": 1,
      "bk_asst_inst_id": 100,
      "bk_relation_type_name": "关联关系",
      "bk_src_model": "bk_host",
      "bk_dst_model": "bk_slb"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
       oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model
FROM cc_InstAsst_0_pub a
JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
WHERE a.bk_inst_id = ? OR a.bk_asst_inst_id = ?
[AND a.bk_obj_id = ?]
```

---

### 22. 获取所有关系类型

**GET /api/relations**

**响应示例:**
```json
{
  "relations": [
    {
      "bk_relation_type_id": "bk_relation",
      "bk_relation_type_name": "关联关系",
      "bk_src_model": "bk_host",
      "bk_dst_model": "bk_slb",
      "cardinality": "1:N"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT 
    oa.bk_asst_id as bk_relation_type_id, 
    ad.bk_asst_name as bk_relation_type_name, 
    oa.bk_obj_id as bk_src_model, 
    oa.target_obj_id as bk_dst_model, 
    oa.cardinality
FROM cc_ObjAsst oa
JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
```

---

### 23. 获取统计数据

**GET /api/statistics**

**响应示例:**
```json
{
  "statistics": {
    "cc_ObjectBase_0_pub_bk_host": 100,
    "cc_ObjectBase_0_pub_bk_slb": 50
  }
}
```

**SQL 查询:**
```sql
SELECT DISTINCT bk_obj_id FROM cc_ObjAttDes
SELECT COUNT(*) as cnt FROM "cc_ObjectBase_0_pub_{model_id}"
```

---

### 24. 获取用户配置

**POST /api/usercustom/user/search**

**请求头:**
- `x-user-name` (string, optional) - 用户名，默认为 "admin"

**响应示例:**
```json
{
  "bk_host_columns": ["id", "bk_host_name", "bk_os_type"],
  "theme": "dark"
}
```

**SQL 查询:**
```sql
SELECT config_key, config_value FROM user_custom WHERE user_name = ?
```

---

### 25. 保存用户配置

**POST /api/usercustom**

**请求头:**
- `x-user-name` (string, optional) - 用户名，默认为 "admin"

**请求体:**
```json
{
  "bk_host_columns": ["id", "bk_host_name", "bk_os_type"],
  "theme": "dark"
}
```

**响应示例:**
```json
{
  "message": "User custom saved successfully",
  "user_name": "admin"
}
```

**SQL 查询:**
```sql
INSERT INTO user_custom (user_name, config_key, config_value, updated_at)
VALUES (?, ?, ?, ?)
ON CONFLICT(user_name, config_key) 
DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
```

---

### 26. 获取用户列表

**GET /api/users**

**响应示例:**
```json
{
  "users": [
    {
      "id": 1,
      "user_name": "admin",
      "display_name": "Administrator",
      "created_at": "2024-01-01 00:00:00"
    }
  ]
}
```

**SQL 查询:**
```sql
SELECT * FROM users ORDER BY id
```

---

### 27. 获取模型的列配置

**GET /api/usercustom/model/{obj_id}**

**路径参数:**
- `obj_id` (string) - 模型ID

**请求头:**
- `x-user-name` (string, optional) - 用户名，默认为 "admin"

**响应示例:**
```json
{
  "columns": ["id", "bk_host_name", "bk_os_type"]
}
```

**SQL 查询:**
```sql
SELECT config_value FROM user_custom WHERE user_name = ? AND config_key = ?
```

---

### 28. 保存模型的列配置

**POST /api/usercustom/model/{obj_id}**

**路径参数:**
- `obj_id` (string) - 模型ID

**请求头:**
- `x-user-name` (string, optional) - 用户名，默认为 "admin"

**请求体:**
```json
{
  "columns": ["id", "bk_host_name", "bk_os_type"]
}
```

**响应示例:**
```json
{
  "message": "Model custom saved successfully",
  "obj_id": "bk_host",
  "columns": ["id", "bk_host_name", "bk_os_type"]
}
```

**SQL 查询:**
```sql
INSERT INTO user_custom (user_name, config_key, config_value, updated_at)
VALUES (?, ?, ?, ?)
ON CONFLICT(user_name, config_key) 
DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
```

---

### 29. 检查实例关联数量

**POST /api/models/{model_id}/instances/check-associations**

**路径参数:**
- `model_id` (string) - 模型ID

**请求体:**
```json
{
  "ids": [1, 2, 3]
}
```

**响应示例:**
```json
{
  "total_associations": 15,
  "source_associations": 10,
  "target_associations": 5,
  "instance_count": 3,
  "model_id": "bk_host"
}
```

**SQL 查询:**
```sql
-- 作为源的关联
SELECT COUNT(*) as count FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN (?, ?, ?)

-- 作为目标的关联
SELECT COUNT(*) as count FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN (?, ?, ?)
```

---

### 30. 创建新的模型实例

**POST /api/models/{model_id}/instances**

**路径参数:**
- `model_id` (string) - 模型ID

**请求体:**
```json
{
  "data": {
    "bk_host_name": "host-001",
    "bk_os_type": "Linux",
    "cpu": 8,
    "memory": 16
  }
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": 1001,
    "bk_host_name": "host-001",
    "bk_os_type": "Linux",
    "create_time": "2024-01-01 00:00:00"
  },
  "message": "实例创建成功"
}
```

**SQL 查询:**
```sql
INSERT INTO "cc_ObjectBase_0_pub_{model_id}" ({columns}) VALUES ({placeholders})
```

---

### 31. 更新单个实例

**PUT /api/models/{model_id}/instances/{instance_id}**

**路径参数:**
- `model_id` (string) - 模型ID
- `instance_id` (int) - 实例ID

**请求体:**
```json
{
  "bk_host_name": "host-001-updated",
  "cpu": 16
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "bk_host_name": "host-001-updated",
    "cpu": 16
  },
  "message": "Instance updated successfully"
}
```

**SQL 查询:**
```sql
UPDATE "cc_ObjectBase_0_pub_{model_id}" SET {update_fields} WHERE id = ?
```

---

### 32. 批量更新实例

**PUT /api/models/{model_id}/instances**

**路径参数:**
- `model_id` (string) - 模型ID

**请求体 - 格式1（每个实例不同数据）:**
```json
{
  "update": [
    {"datas": {"bk_host_name": "host-001"}, "inst_id": 1},
    {"datas": {"bk_host_name": "host-002"}, "inst_id": 2}
  ]
}
```

**请求体 - 格式2（多个实例相同数据）:**
```json
{
  "ids": [1, 2, 3],
  "data": {"bk_os_type": "Linux"}
}
```

**响应示例:**
```json
{
  "success": true,
  "updated_count": 3,
  "updated_ids": [1, 2, 3],
  "message": "Successfully updated 3 instances"
}
```

**SQL 查询:**
```sql
UPDATE "cc_ObjectBase_0_pub_{model_id}" SET {update_fields} WHERE id IN ({placeholders})
```

---

### 33. 删除实例

**DELETE /api/models/{model_id}/instances**

**路径参数:**
- `model_id` (string) - 模型ID

**请求体:**
```json
{
  "ids": [1, 2, 3]
}
```

**响应示例:**
```json
{
  "deleted_count": 3,
  "ids": [1, 2, 3],
  "message": "Successfully deleted 3 instances"
}
```

**SQL 查询:**
```sql
-- 删除关联表中的记录
DELETE FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN ({placeholders})
DELETE FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN ({placeholders})

-- 删除实例表中的记录
DELETE FROM "cc_ObjectBase_0_pub_{model_id}" WHERE id IN ({placeholders})
```

---

## 关键注意点

### 1. 动态表名处理
- 实例表名格式：`cc_ObjectBase_0_pub_{model_id}`
- 需要对表名进行安全验证，防止 SQL 注入

### 2. 字段安全验证
- 过滤系统字段（id, create_time, last_time, bk_supplier_account）
- 跳过只读字段（isreadonly=True）
- 字段名仅允许字母、数字和下划线

### 3. 参数化查询
- 所有查询必须使用参数化查询
- 禁止字符串拼接 SQL

### 4. 数据验证
- 必填字段验证（isrequired=True）
- 枚举值验证（option字段）
- 正则表达式验证（singlechar/longchar类型）

### 5. DuckDB 特性
- DuckDB 使用 `?` 作为参数占位符
- 日期时间格式为 `'%Y-%m-%d %H:%M:%S'`
- INTEGER PRIMARY KEY 不会自动递增，需手动生成

---

## SQL 文件模板化

### 模板结构

```
app/sql/
├── classification/
│   ├── select_classifications.sql
│   ├── select_classification_by_id.sql
│   └── select_models_by_classification.sql
├── model/
│   ├── select_models.sql
│   ├── select_model_by_id.sql
│   └── select_model_attributes.sql
├── instance/
│   ├── select_instances.sql
│   ├── select_instance_by_id.sql
│   ├── insert_instance.sql
│   ├── update_instance.sql
│   └── delete_instance.sql
├── association/
│   ├── select_association_types.sql
│   ├── select_object_associations.sql
│   ├── select_instance_associations.sql
│   ├── insert_instance_association.sql
│   └── delete_instance_association.sql
├── relation/
│   └── select_relations.sql
├── user/
│   ├── select_users.sql
│   ├── select_user_custom.sql
│   └── insert_or_update_user_custom.sql
└── common/
    ├── page_limit.sql
    └── statistics.sql
```

### 模板示例

#### select_instances.sql
```sql
-- 获取模型实例列表
-- 参数: :model_id, :where_clause, :order_clause, :limit, :offset
SELECT * FROM "cc_ObjectBase_0_pub_:model_id"
{% if where_clause %}WHERE :where_clause{% endif %}
{% if order_clause %}ORDER BY :order_clause{% endif %}
LIMIT :limit OFFSET :offset
```

#### insert_instance.sql
```sql
-- 插入实例
-- 参数: :columns, :placeholders, :values
INSERT INTO "cc_ObjectBase_0_pub_:model_id" (:columns)
VALUES (:placeholders)
```

#### select_user_custom.sql
```sql
-- 获取用户配置
-- 参数: :user_name
SELECT config_key, config_value FROM user_custom WHERE user_name = :user_name
```

---

## DuckDB SQL 转 sqlglot 规范

### 转换规则

| DuckDB 特性 | 标准 SQL 转换 | 说明 |
|-------------|--------------|------|
| `?` 参数占位符 | `:name` 命名参数 | sqlglot 使用命名参数 |
| `NEXTVAL('seq')` | `NEXT VALUE FOR seq` | 序列语法标准化 |
| `CAST(x AS VARCHAR)` | `CAST(x AS TEXT)` | 类型名称统一 |
| `LOWER()` | `LOWER()` | 保持不变 |
| `LIKE LOWER()` | `ILIKE` | 不区分大小写匹配 |

### 转换示例

**DuckDB SQL:**
```sql
SELECT * FROM users WHERE LOWER(name) LIKE LOWER('%:keyword%')
```

**转换后（SQLite）:**
```sql
SELECT * FROM users WHERE name ILIKE '%:keyword%'
```

**转换后（PostgreSQL）:**
```sql
SELECT * FROM users WHERE name ILIKE '%:keyword%'
```

---

**文档生成时间:** 2026-05-29
