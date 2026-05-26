# CMDB Server Lite 数据库规则文档

## 概述

本文档定义了 cmdb_server_lite 项目中数据库表的命名规则、字段规则，以及与原项目（蓝鲸 CMDB）的对应关系。

**文档版本**：
- 基于：cmdb_server_lite（DuckDB 版本）
- 规则变更历史：
  - v1.0 - 初始版本，表结构与原项目保持一致（cc_ 前缀）
  - v1.1 - 移除自定义 `relations` 表，回归原项目的 `cc_AsstDes` + `cc_ObjAsst` 结构
  - v1.2 - 实现动态模型表名，移除硬编码 `table_map`

---

## 一、表命名规则

### 1.1 命名前缀统一

所有表名必须使用 `cc_` 前缀，与原项目蓝鲸 CMDB 保持一致。

### 1.2 表分类规则

| 表类型 | 命名格式 | 示例 | 说明 |
|--------|---------|------|------|
| 模型定义 | `cc_ObjDes` | `cc_ObjDes` | 对象/模型描述表（唯一） |
| 属性定义 | `cc_ObjAttDes` | `cc_ObjAttDes` | 对象属性描述表（唯一） |
| 关联类型 | `cc_AsstDes` | `cc_AsstDes` | 关联描述表（唯一） |
| 对象关联 | `cc_ObjAsst` | `cc_ObjAsst` | 对象关联关系表（唯一） |
| 实例关联 | `cc_InstAsst_{supplier}_pub` | `cc_InstAsst_0_pub` | 实例关联关系表（按供应商分表） |
| 实例数据 | `cc_ObjectBase_{supplier}_pub_{obj_id}` | `cc_ObjectBase_0_pub_bk_host` | 各模型实例表（按模型分表） |

### 1.3 分表规则

1. **供应商分表**：`{supplier}` - 默认值为 `0`
2. **模型分表**：`{obj_id}` - 模型ID，来自 `cc_ObjDes.bk_obj_id`

---

## 二、表结构详解

### 2.1 cc_ObjDes - 对象/模型定义表

**作用**：存放所有模型的元数据定义

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID（原项目MongoDB兼容） |
| `id` | INTEGER | 否 | 整数ID |
| `bk_obj_id` | VARCHAR | 是 | 模型ID（主键） |
| `bk_obj_name` | VARCHAR | 是 | 模型名称 |
| `bk_obj_icon` | VARCHAR | 否 | 模型图标 |
| `bk_classification_id` | VARCHAR | 否 | 分类ID |
| `bk_ishidden` | BOOLEAN | 否 | 是否隐藏（默认false） |
| `ispre` | BOOLEAN | 否 | 是否预置模型（默认false） |
| `bk_ispaused` | BOOLEAN | 否 | 是否暂停（默认false） |
| `position` | VARCHAR | 否 | 排序位置 |
| `creator` | VARCHAR | 否 | 创建者（默认admin） |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） |
| `create_time` | TIMESTAMP | 否 | 创建时间（默认CURRENT_TIMESTAMP） |
| `last_time` | TIMESTAMP | 否 | 最后修改时间（默认CURRENT_TIMESTAMP） |
| `obj_sort_number` | INTEGER | 否 | 排序编号（默认0） |
| bk_supplier_account | VARCHAR | 否 | 供应商账号（默认0） |

---

### 2.2 cc_ObjAttDes - 对象属性定义表

**作用**：定义模型的属性字段

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `id` | INTEGER | 否 | 整数ID |
| `bk_obj_id` | VARCHAR | 是 | 所属模型ID |
| `bk_property_id` | VARCHAR | 是 | 属性ID（唯一标识） |
| `bk_property_name` | VARCHAR | 是 | 属性名称 |
| `bk_property_type` | VARCHAR | 是 | 属性类型 |
| `bk_property_group` | VARCHAR | 否 | 属性分组 |
| `isrequired` | BOOLEAN | 否 | 是否必填（默认false） |
| `bk_ispassword` | BOOLEAN | 否 | 是否密码字段（默认false） |
| `bk_ishidden` | BOOLEAN | 否 | 是否隐藏（默认false） |
| `isreadonly` | BOOLEAN | 否 | 是否只读（默认false） |
| `bk_isapi` | BOOLEAN | 否 | 是否API字段（默认false） |
| `option` | VARCHAR | 否 | 选项配置 |
| `unit` | VARCHAR | 否 | 单位 |
| `placeholder` | VARCHAR | 否 | 占位符 |
| `editable` | BOOLEAN | 否 | 是否可编辑（默认true） |
| `ispre` | BOOLEAN | 否 | 是否预置属性（默认false） |
| `bk_property_index` | INTEGER | 否 | 属性排序索引 |
| `creator` | VARCHAR | 否 | 创建者（默认admin） |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） |
| `create_time` | TIMESTAMP | 否 | 创建时间 |
| `last_time` | TIMESTAMP | 否 | 最后修改时间 |
| bk_supplier_account | VARCHAR | 否 | 供应商账号（默认0） |

---

### 2.3 cc_AsstDes - 关联类型定义表

**作用**：定义关联关系的类型

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `bk_asst_id` | VARCHAR | 是 | 关联类型ID（主键） |
| `bk_asst_name` | VARCHAR | 是 | 关联类型名称 |
| `src_des` | VARCHAR | 否 | 源端描述 |
| `dest_des` | VARCHAR | 否 | 目标端描述 |
| direction | VARCHAR | 否 | 方向（forward） |
| ispre | BOOLEAN | 否 | 是否预置（默认false） |
| bk_supplier_account | VARCHAR | 否 | 供应商账号（默认0） |

---

### 2.4 cc_ObjAsst - 对象关联关系表

**作用**：定义模型与模型之间的关联关系

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `bk_obj_id` | VARCHAR | 是 | 源对象ID |
| `target_obj_id` | VARCHAR | 是 | 目标对象ID |
| `target_obj_name` | VARCHAR | 是 | 目标对象名称 |
| `bk_asst_id` | VARCHAR | 是 | 关联类型ID（外键到cc_AsstDes） |
| `bk_obj_asst_id` | VARCHAR | 是 | 对象关联ID（主键） |
| `bk_obj_asst_name` | VARCHAR | 是 | 对象关联名称 |
| `cardinality` | VARCHAR | 是 | 基数（1:1, 1:n, n:n） |
| `mapping` | VARCHAR | 否 | 映射规则 |
| `on_delete` | VARCHAR | 否 | 删除策略 |
| `creator` | VARCHAR | 否 | 创建者（默认admin） |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） |
| `create_time` | TIMESTAMP | 否 | 创建时间 |
| `last_time` | TIMESTAMP | 否 | 最后修改时间 |
| bk_supplier_account | VARCHAR | 否 | 供应商账号（默认0） |

**关联ID命名规则**：
- 格式：`{bk_obj_id}_to_{target_obj_id}`
- 示例：`bk_host_to_bk_switch`

---

### 2.5 cc_InstAsst_0_pub - 实例关联关系表

**作用**：存储实例之间的具体关联数据

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `id` | INTEGER | 是 | 关联ID（主键） |
| `bk_obj_id` | VARCHAR | 是 | 源模型ID |
| `bk_inst_id` | INTEGER | 是 | 源实例ID |
| `bk_asst_obj_id` | VARCHAR | 是 | 目标模型ID |
| `bk_asst_inst_id` | INTEGER | 是 | 目标实例ID |
| `bk_obj_asst_id` | VARCHAR | 是 | 对象关联ID（外键到cc_ObjAsst） |
| bk_relation_type_id | VARCHAR | 是 | 关联类型ID（外键到cc_AsstDes） |

---

### 2.6 cc_ObjectBase_0_pub_{obj_id} - 模型实例表

**作用**：存储具体模型的实例数据，每个模型对应一个分表

**表命名**：`cc_ObjectBase_{supplier}_pub_{bk_obj_id}`
- `{supplier}` - 供应商（默认 0）
- `{bk_obj_id}` - 模型ID（来自 cc_ObjDes）

**示例**：
- `cc_ObjectBase_0_pub_bk_host` - 主机实例表
- `cc_ObjectBase_0_pub_bk_switch` - 交换机实例表
- `cc_ObjectBase_0_pub_bk_slb` - SLB实例表

**通用表结构**（所有实例表必须包含的字段）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `id` | INTEGER | 是 | 实例ID（主键） |
| `bk_inst_id` | INTEGER | 是 | 蓝鲸实例ID（全局唯一） |
| `bk_inst_name` | VARCHAR | 是 | 实例名称 |
| `bk_supplier_account` | VARCHAR | 否 | 供应商账号（默认0） |
| `bk_obj_id` | VARCHAR | 是 | 所属模型ID |
| `create_time` | TIMESTAMP | 否 | 创建时间 |
| `last_time` | TIMESTAMP | 否 | 最后修改时间 |
| bk_operate_time | TIMESTAMP | 否 | 操作时间 |

**示例表结构**（bk_host）：

| 自定义字段 | 类型 | 说明 |
|-----------|------|------|
| `bk_host_name` | VARCHAR | 主机名 |
| `bk_host_innerip` | VARCHAR | 内网IP |
| `bk_cloud_id` | INTEGER | 云区域ID |
| `bk_agent_id` | VARCHAR | Agent ID |
| `bk_cloud_vendor` | VARCHAR | 云厂商 |

---

## 三、字段规则

### 3.1 通用字段规则

1. **必填字段**：
   - 所有表的主键字段必须存在
   - 实例表必须包含：`id`, `bk_inst_id`, `bk_inst_name`, `bk_obj_id`

2. **时间字段**：
   - 使用 `TIMESTAMP` 类型
   - 默认值为 `CURRENT_TIMESTAMP`

3. **布尔字段**：
   - 使用 `BOOLEAN` 类型
   - 默认值明确标注

4. **字符串字段**：
   - 使用 `VARCHAR` 类型
   - 长度无严格限制（DuckDB 特性）

### 3.2 bk_inst_id 和 bk_inst_name 特殊规则

#### 内置模型特殊映射

原项目对内置模型有固定的 ID 和 NAME 字段映射：

| 模型ID | ID字段 | NAME字段 |
|--------|--------|----------|
| `bk_biz_set_obj` | `bk_biz_set_id` | `bk_biz_set_name` |
| `biz` | `bk_biz_id` | `bk_biz_name` |
| `host` | `bk_host_id` | `bk_host_name` |
| `module` | `bk_module_id` | `bk_module_name` |
| `set` | `bk_set_id` | `bk_set_name` |
| `bk_project` | `id` | `bk_project_name` |

#### 自定义模型规则

对于非内置的自定义模型（如 `bk_slb`, `bk_switch` 等）：
- **ID 字段**：`bk_inst_id`（通用实例ID，正整数类型）
- **名称字段**：`bk_inst_name`（通用实例名称）

#### bk_inst_id 特殊属性

- 数据类型：正整数（POSITIVE_INTEGER）
- 搜索行为：粘贴导入时会进行强制分割验证
- 关联场景：在实例关联中作为源实例或目标实例的标识

---

## 四、与原项目对比

| 原项目 (MongoDB) | Lite项目 (DuckDB) | 状态 |
|------------------|-------------------|------|
| `cc_ObjDes` | `cc_ObjDes` | ✅ 完全一致 |
| `cc_ObjAttDes` | `cc_ObjAttDes` | ✅ 完全一致 |
| `cc_AsstDes` | `cc_AsstDes` | ✅ 完全一致 |
| `cc_ObjAsst` | `cc_ObjAsst` | ✅ 完全一致 |
| `cc_InstAsst_{supplier}_pub` | `cc_InstAsst_0_pub` | ✅ 完全一致 |
| `cc_ObjectBase_{supplier}_pub_{obj}` | `cc_ObjectBase_0_pub_{obj}` | ✅ 完全一致 |
| `cc_ObjClassification` | （简化） | ⚠️ 暂未实现 |
| `cc_PropertyGroup` | （简化） | ⚠️ 暂未实现 |

---

## 五、新增模型标准步骤

### 步骤 1: 在 cc_ObjDes 中添加模型定义

```sql
INSERT INTO cc_ObjDes (bk_obj_id, bk_obj_name, ispre, bk_supplier_account)
VALUES ('bk_custom_model', '自定义模型', true, '0');
```

### 步骤 2: 在 cc_ObjAttDes 中添加属性

```sql
INSERT INTO cc_ObjAttDes (
    bk_obj_id, bk_property_id, bk_property_name, bk_property_type,
    isrequired, ispre, bk_property_index, bk_supplier_account
) VALUES (
    'bk_custom_model', 'name', '名称', 'string',
    true, true, 1, '0'
);
```

### 步骤 3: 创建实例表

```sql
CREATE TABLE cc_ObjectBase_0_pub_bk_custom_model (
    _id VARCHAR,
    id INTEGER PRIMARY KEY,
    bk_inst_id INTEGER,
    bk_inst_name VARCHAR,
    bk_supplier_account VARCHAR DEFAULT '0',
    bk_obj_id VARCHAR,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 自定义字段
    name VARCHAR,
    description VARCHAR
);
```

### 步骤 4: 如需关联，在 cc_AsstDes 和 cc_ObjAsst 中定义

---

## 六、参考文件

- **数据库迁移脚本**：[migrate_data.py](file:///workspace/bk-cmdb/cmdb_server_lite/migrate_data.py)
- **API服务主文件**：[main.py](file:///workspace/bk-cmdb/cmdb_server_lite/main.py)
- **原项目表结构**：[tablenames.go](file:///workspace/bk-cmdb/src/common/tablenames.go)
- **原项目UI常量**：[model-constants.js](file:///workspace/bk-cmdb/src/ui/src/dictionary/model-constants.js)
- **原项目UI属性**：[property-constants.js](file:///workspace/bk-cmdb/src/ui/src/dictionary/property-constants.js)

---

**文档维护**：本文档随代码更新，请保持同步。
