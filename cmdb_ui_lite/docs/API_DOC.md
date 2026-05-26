# CMDB UI Lite API 接口文档

## 概述

本项目采用 Mock JSON 数据模拟真实 API 接口，实现与原项目 bk-cmdb 相同的数据结构和接口规范。

## 文件结构

```
src/assets/api/
├── index.json                      # 模型索引文件
└── models/
    ├── attributes/                 # 模型属性接口
    │   ├── bk_switch.json         # 交换机属性
    │   ├── bk_host.json          # 主机属性
    │   ├── bk_slb.json           # 负载均衡属性
    │   ├── bk_slb_server.json    # 后端服务器属性
    │   └── bk_slb_listener.json  # 监听器属性
    ├── instances/                 # 实例数据接口
    │   ├── bk_switch.json        # 交换机实例
    │   ├── bk_host.json          # 主机实例
    │   ├── bk_slb.json           # 负载均衡实例
    │   ├── bk_slb_server.json    # 后端服务器实例
    │   └── bk_slb_listener.json  # 监听器实例
    ├── relations/                 # 模型关联定义
    │   └── bk_slb.json           # SLB 关联关系定义
    └── associations/              # 实例关联数据
        └── bk_slb.json           # SLB 实例关联关系
```

---

## 1. 模型索引接口

### GET /api/index.json

模型索引文件，包含所有可用模型的元信息和关联关系。

**响应格式：**

```json
{
  "models": [
    {
      "bk_obj_id": "bk_slb",
      "bk_obj_name": "负载均衡",
      "bk_obj_icon": "icon-cc-loadbalance",
      "attributes_file": "attributes/bk_slb.json",
      "instances_file": "instances/bk_slb.json",
      "relations_file": "relations/bk_slb.json",
      "associations_file": "associations/bk_slb.json",
      "associations": [
        {
          "target_obj_id": "bk_slb_server",
          "target_obj_name": "后端服务器",
          "relation_type_id": "slb_to_server",
          "relation_type_name": "SLB后端服务器",
          "cardinality": "1:n",
          "direction": "forward"
        }
      ]
    }
  ]
}
```

---

## 2. 模型属性接口

### GET /api/models/attributes/{model_id}.json

获取指定模型的属性列表，对应原项目 `find/objectattr` 接口。

**响应格式：**

```json
{
  "info": [
    {
      "bk_property_id": "id",
      "bk_property_name": "实例ID",
      "bk_property_type": "int",
      "isrequired": false,
      "isreadonly": true,
      "editable": false,
      "bk_property_index": -1,
      "width": 120,
      "option": []
    }
  ],
  "default_columns": ["id", "name", "management_ip"]
}
```

---

## 3. 实例数据接口

### GET /api/models/instances/{model_id}.json

获取指定模型的实例列表，对应原项目 `find/instassociation/object/{objId}` 接口。

**响应格式：**

```json
{
  "info": [
    {
      "id": 1,
      "name": "core-switch-01",
      "management_ip": "192.168.0.1"
    }
  ]
}
```

---

## 4. 模型关联定义接口

### GET /api/models/relations/{model_id}.json

获取指定模型的关联关系定义，对应原项目 `find/associationtype` 接口。

**响应格式：**

```json
{
  "relations": [
    {
      "bk_obj_id": "bk_slb",
      "bk_relation_type_id": "slb_to_server",
      "bk_relation_type_name": "SLB后端服务器",
      "bk_asst_obj_id": "bk_slb_server",
      "mapping": {
        "bk_slb": {
          "key": "id",
          "label": "bk_lb_name"
        },
        "bk_slb_server": {
          "key": "bk_slb_id",
          "label": "bk_slb_name"
        }
      },
      "cardinality": "1:n",
      "direction": "src_to_dst"
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bk_obj_id | string | 是 | 源模型ID |
| bk_relation_type_id | string | 是 | 关联类型ID |
| bk_relation_type_name | string | 是 | 关联类型名称 |
| bk_asst_obj_id | string | 是 | 目标模型ID |
| mapping | object | 是 | 关联字段映射 |
| cardinality | string | 是 | 基数 (1:1, 1:n, n:n) |
| direction | string | 是 | 关联方向 |

---

## 5. 实例关联数据接口

### GET /api/models/associations/{model_id}.json

获取指定模型的实例关联数据，对应原项目 `find/instassociation/object/{objId}` 接口。

**响应格式：**

```json
{
  "associations": [
    {
      "id": 1,
      "bk_obj_id": "bk_slb",
      "bk_inst_id": 1,
      "bk_asst_obj_id": "bk_slb_server",
      "bk_asst_inst_id": 1,
      "bk_relation_type_id": "slb_to_server"
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | number | 是 | 关联记录ID |
| bk_obj_id | string | 是 | 源模型ID |
| bk_inst_id | number | 是 | 源实例ID |
| bk_asst_obj_id | string | 是 | 目标模型ID |
| bk_asst_inst_id | number | 是 | 目标实例ID |
| bk_relation_type_id | string | 是 | 关联类型ID |

---

## 6. SLB 模型关联关系

### 6.1 关联拓扑

```
bk_slb (负载均衡)
    │
    ├── 1:n ──→ bk_slb_server (后端服务器)
    │           关联类型: slb_to_server
    │           基数: 1:n
    │
    └── 1:n ──→ bk_slb_listener (监听器)
                关联类型: slb_to_listener
                基数: 1:n
```

### 6.2 实例关联关系表

| SLB实例 | 后端服务器 | 监听器 |
|---------|------------|--------|
| web-slb-public (id=1) | web-server-01, web-server-02, web-server-03 | http-80, https-443, ws-8080 |
| api-slb-internal (id=2) | api-server-01, api-server-02, api-server-03 | api-grpc-9000, api-rest-8000 |
| https-slb-ssl (id=3) | video-edge-01 | https-api-8443, https-web-443, udp-dns-53 |
| cache-slb-redis (id=4) | redis-server-01, redis-server-02 | redis-cluster-6379 |
| db-slb-read (id=5) | db-reader-01, db-reader-02 | mysql-ro-3306, mysql-ro-3307 |
| cdn-slb-origin (id=6) | cdn-origin-01 | http-origin-80 |
| video-slb-stream (id=7) | - | rtmp-1935, hls-8080, flv-8081 |
| backup-slb-dr (id=8) | - | - |

---

## 7. 模型详情

### 7.1 交换机 (bk_switch)

**属性数量：** 33 个
**实例数量：** 10 条

**默认显示列：** `["id", "name", "management_ip", "model", "vendor", "vlan", "biz_name"]`

---

### 7.2 主机 (bk_host)

**属性数量：** 21 个
**实例数量：** 10 条

**默认显示列：** `["id", "bk_host_innerip", "bk_host_name", "os_type", "cpu", "bk_disk", "bk_mem", "bk_biz_name"]`

---

### 7.3 负载均衡 (bk_slb)

**属性数量：** 18 个
**实例数量：** 8 条

**关联关系：**

| 目标模型 | 关联类型 | 基数 | 说明 |
|----------|----------|------|------|
| bk_slb_server | slb_to_server | 1:n | SLB后端服务器 |
| bk_slb_listener | slb_to_listener | 1:n | SLB监听器 |

**默认显示列：** `["id", "bk_lb_name", "bk_lb_type", "bk_lb_algorithm", "bk_lb_ip", "bk_region", "bk_status", "bk_biz_name"]`

---

### 7.4 后端服务器 (bk_slb_server)

**属性数量：** 15 个
**实例数量：** 12 条

**关联关系：**

| 目标模型 | 关联类型 | 基数 | 说明 |
|----------|----------|------|------|
| bk_slb | server_to_slb | n:1 | 所属SLB |

**默认显示列：** `["id", "bk_server_name", "bk_server_ip", "bk_server_port", "bk_weight", "bk_health_status", "bk_server_status", "bk_slb_id"]`

---

### 7.5 监听器 (bk_slb_listener)

**属性数量：** 16 个
**实例数量：** 15 条

**关联关系：**

| 目标模型 | 关联类型 | 基数 | 说明 |
|----------|----------|------|------|
| bk_slb | listener_to_slb | n:1 | 所属SLB |

**默认显示列：** `["id", "bk_listener_name", "bk_protocol", "bk_frontend_port", "bk_backend_port", "bk_scheduler", "bk_slb_id", "bk_status"]`

---

## 8. 与原项目 API 对应关系

| 本项目 Mock 接口 | 原项目 API | 说明 |
|-----------------|------------|------|
| attributes/*.json | find/objectattr | 查询对象属性 |
| instances/*.json | find/instassociation/object/{objId} | 查询实例列表 |
| relations/*.json | find/associationtype | 查询关联类型 |
| associations/*.json | find/instassociation/object/{objId} | 查询实例关联关系 |
| index.json | - | 自定义索引文件 |

---

## 9. 更新日志

### v1.1.0 (2024-05-08)
- 新增模型关联功能
- 新增 SLB 模型的关联定义和实例关联数据
- 支持 1:n 和 n:1 关联关系

### v1.0.0 (2024-05-08)
- 初始版本
- 支持 5 个模型：交换机、主机、负载均衡、后端服务器、监听器
- 所有模型包含完整的属性定义和示例数据
