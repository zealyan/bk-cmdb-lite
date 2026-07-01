# CMDB Server Lite 数据库规则文档

## 概述

本文档定义了 cmdb_server_lite 项目中数据库表的命名规则、字段规则、技术架构，以及与原项目（蓝鲸 CMDB）的对应关系。

**文档版本**：
- 基于：cmdb_server_lite（SQLAlchemy + 多数据库支持版本）
- 规则变更历史：
  - v1.0 - 初始版本，表结构与原项目保持一致（cc_ 前缀）
  - v1.1 - 移除自定义 `relations` 表，回归原项目的 `cc_AsstDes` + `cc_ObjAsst` 结构
  - v1.2 - 实现动态模型表名，移除硬编码 `table_map`
  - **v2.0** - 数据库架构重构，从 DuckDB 迁移到 SQLAlchemy 2.0+ + 多数据库支持（SQLite/MySQL/PostgreSQL）
  - **v2.3** - 补充原项目 `Attribute` 结构体所有字段的 bson 标签对照，整理完整 MongoDB 表映射关系
  - **v2.4** - 统一属性类型规范，移除 `string` 类型，使用 `singlechar`/`shortchar`/`longchar`/`text` 替代，与原项目蓝鲸 CMDB 保持一致

---

## 一、数据库技术架构

### 1.1 数据库技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **连接池** | SQLAlchemy | >=2.0.35 | 数据库连接池管理 |
| **方言处理** | sqlglot | 19.8.0 | 多数据库 SQL 方言转换 |
| **驱动** | psycopg2-binary | 2.9.7 | PostgreSQL 驱动 |
| **驱动** | pymysql | 1.1.0 | MySQL 驱动 |
| **内置** | sqlite3 | Python 3.9 | SQLite 驱动 |

### 1.2 支持的数据库类型

```python
class DatabaseType(Enum):
    """支持的数据库类型"""
    SQLITE = 'sqlite'       # 开发环境默认
    POSTGRESQL = 'postgresql'  # 生产环境推荐
    MYSQL = 'mysql'         # 生产环境可选
    DUCKDB = 'duckdb'       # 兼容旧版本
```

### 1.3 数据库配置

**开发环境配置**（默认）：
```python
DATABASE_TYPE = 'sqlite'
DATABASE_NAME = 'cmdb_dev.db'
SQLALCHEMY_ECHO = True  # SQL 日志开启
```

**生产环境配置**：
```python
DATABASE_TYPE = 'postgresql'
DATABASE_USER = 'xxx'
DATABASE_PASSWORD = 'xxx'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'
DATABASE_NAME = 'cmdb_prod'
```

### 1.4 连接池配置

```python
SQLALCHEMY_POOL_SIZE = 5          # 连接池大小
SQLALCHEMY_MAX_OVERFLOW = 10     # 最大溢出连接数
SQLALCHEMY_POOL_RECYCLE = 3600    # 连接回收时间（秒）
SQLALCHEMY_ECHO = False           # 是否输出 SQL 日志
```

---

## 二、表命名规则

### 2.1 命名前缀统一

所有表名必须使用 `cc_` 前缀，与原项目蓝鲸 CMDB 保持一致。

### 2.2 表分类规则

| 表类型 | 命名格式 | 示例 | 说明 |
|--------|---------|------|------|
| 模型定义 | `cc_ObjDes` | `cc_ObjDes` | 对象/模型描述表（唯一） |
| 属性定义 | `cc_ObjAttDes` | `cc_ObjAttDes` | 对象属性描述表（唯一） |
| 关联类型 | `cc_AsstDes` | `cc_AsstDes` | 关联描述表（唯一） |
| 对象关联 | `cc_ObjAsst` | `cc_ObjAsst` | 对象关联关系表（唯一） |
| 实例关联 | `cc_InstAsst_0_pub` | `cc_InstAsst_0_pub` | 实例关联关系表（按供应商分表） |
| 实例数据 | `cc_ObjectBase_0_pub_{obj_id}` | `cc_ObjectBase_0_pub_bk_host` | 各模型实例表（按模型分表） |

### 2.3 分表规则

1. **供应商分表**：`{supplier}` - 默认值为 `0`
2. **模型分表**：`{obj_id}` - 模型ID，来自 `cc_ObjDes.bk_obj_id`

---

## 三、表结构详解

### 3.1 cc_ObjDes - 对象/模型定义表

**作用**：存放所有模型的元数据定义，对应原项目 MongoDB 表 `cc_ObjDes`（见 [tablenames.go](file:///workspace/bk-cmdb/src/common/tablenames.go#L32-L33)）

**表结构**（基于原项目 [Object 结构体](file:///workspace/bk-cmdb/src/common/metadata/object.go#L63-L83)）：

| 字段 | 类型 | 必填 | 说明 | BSON标签 |
|------|------|------|------|----------|
| `_id` | VARCHAR | 否 | 内部唯一ID（原项目MongoDB兼容） | `_id` |
| `id` | INTEGER | 否 | 整数ID | `id` |
| `bk_classification_id` | VARCHAR | 否 | 分类ID | `bk_classification_id` |
| `bk_obj_icon` | VARCHAR | 否 | 模型图标 | `bk_obj_icon` |
| `bk_obj_id` | VARCHAR | 是 | 模型ID（主键） | `bk_obj_id` |
| `bk_obj_name` | VARCHAR | 是 | 模型名称 | `bk_obj_name` |
| `bk_ishidden` | BOOLEAN | 否 | 是否隐藏（默认false） | `bk_ishidden` |
| `ispre` | BOOLEAN | 否 | 是否预置模型（默认false） | `ispre` |
| `bk_ispaused` | BOOLEAN | 否 | 是否暂停（默认false） | `bk_ispaused` |
| `position` | VARCHAR | 否 | 排序位置 | `position` |
| `bk_supplier_account` | VARCHAR | 否 | 供应商账号（默认0） | `bk_supplier_account` |
| `description` | VARCHAR | 否 | 描述 | `description` |
| `creator` | VARCHAR | 否 | 创建者（默认admin） | `creator` |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） | `modifier` |
| `create_time` | TIMESTAMP | 否 | 创建时间（默认CURRENT_TIMESTAMP） | `create_time` |
| `last_time` | TIMESTAMP | 否 | 最后修改时间（默认CURRENT_TIMESTAMP） | `last_time` |
| `obj_sort_number` | INTEGER | 否 | 排序编号（默认0） | `obj_sort_number` |

---

### 3.2 cc_ObjAttDes - 对象属性定义表

**作用**：定义模型的属性字段，对应原项目 MongoDB 表 `cc_ObjAttDes`（见 [tablenames.go](file:///workspace/bk-cmdb/src/common/tablenames.go#L38-L39)）

**表结构**（基于原项目 [Attribute 结构体](file:///workspace/bk-cmdb/src/common/metadata/attribute.go#L106-L134)）：

| 字段 | 类型 | 必填 | 说明 | BSON标签 |
|------|------|------|------|----------|
| `_id` | VARCHAR | 否 | 内部唯一ID | `_id` |
| `bk_biz_id` | INTEGER | 否 | 业务ID | `bk_biz_id` |
| `id` | INTEGER | 否 | 整数ID | `id` |
| `bk_supplier_account` | VARCHAR | 否 | 供应商账号（默认0） | `bk_supplier_account` |
| `bk_obj_id` | VARCHAR | 是 | 所属模型ID | `bk_obj_id` |
| `bk_property_id` | VARCHAR | 是 | 属性ID（唯一标识） | `bk_property_id` |
| `bk_property_name` | VARCHAR | 是 | 属性名称 | `bk_property_name` |
| `bk_property_group` | VARCHAR | 否 | 属性分组 | `bk_property_group` |
| `bk_property_group_name` | VARCHAR | 否 | 属性分组名称（不存储） | `-` |
| `bk_property_index` | INTEGER | 否 | 属性排序索引 | `bk_property_index` |
| `unit` | VARCHAR | 否 | 单位 | `unit` |
| `placeholder` | VARCHAR | 否 | 占位符 | `placeholder` |
| `editable` | BOOLEAN | 否 | 是否可编辑（默认true） | `editable` |
| `ispre` | BOOLEAN | 否 | 是否预置属性（默认false） | `ispre` |
| `isrequired` | BOOLEAN | 否 | 是否必填（默认false） | `isrequired` |
| `isreadonly` | BOOLEAN | 否 | 是否只读（默认false） | `isreadonly` |
| `isonly` | BOOLEAN | 否 | 是否唯一（默认false） | `isonly` |
| `bk_issystem` | BOOLEAN | 否 | 是否系统字段（默认false） | `bk_issystem` |
| `bk_isapi` | BOOLEAN | 否 | 是否API字段（默认false） | `bk_isapi` |
| `bk_property_type` | VARCHAR | 是 | 属性类型 | `bk_property_type` |
| `option` | VARCHAR | 否 | 选项配置（JSON序列化存储） | `option` |
| `default` | VARCHAR | 否 | 默认值 | `default` |
| `ismultiple` | BOOLEAN | 否 | 是否多选（默认false），配合 `enummulti` 类型使用 | `ismultiple` |
| `description` | VARCHAR | 否 | 描述 | `description` |
| `bk_template_id` | INTEGER | 否 | 模板ID | `bk_template_id` |
| `creator` | VARCHAR | 否 | 创建者（默认admin） | `creator` |
| `create_time` | TIMESTAMP | 否 | 创建时间 | `create_time` |
| `last_time` | TIMESTAMP | 否 | 最后修改时间 | `last_time` |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） | `modifier` |

**注意**：`option` 字段在数据库中存储为 JSON 序列化字符串（如 `"[\"选项1\", \"选项2\"]"`），后端 API 会自动反序列化为数组返回给前端。

---

### 3.3 cc_AsstDes - 关联类型定义表

**作用**：定义关联关系的类型

**表结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_id` | VARCHAR | 否 | 内部唯一ID |
| `bk_asst_id` | VARCHAR | 是 | 关联类型ID（主键） |
| `bk_asst_name` | VARCHAR | 是 | 关联类型名称 |
| `src_des` | VARCHAR | 否 | 源端描述 |
| `dest_des` | VARCHAR | 否 | 目标端描述 |
| `direction` | VARCHAR | 否 | 方向（forward） |
| `ispre` | BOOLEAN | 否 | 是否预置（默认false） |
| `bk_supplier_account` | VARCHAR | 否 | 供应商账号（默认0） |

---

### 3.4 cc_ObjAsst - 对象关联关系表

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
| `cardinality` | VARCHAR | 否 | 基数（1:1, 1:n, n:n） |
| `mapping` | VARCHAR | 否 | 映射规则 |
| `on_delete` | VARCHAR | 否 | 删除策略 |
| `creator` | VARCHAR | 否 | 创建者（默认admin） |
| `modifier` | VARCHAR | 否 | 修改者（默认admin） |
| `create_time` | TIMESTAMP | 否 | 创建时间 |
| `last_time` | TIMESTAMP | 否 | 最后修改时间 |
| `bk_supplier_account` | VARCHAR | 否 | 供应商账号（默认0） |

**关联ID命名规则**：
- 格式：`{bk_obj_id}_to_{target_obj_id}`
- 示例：`bk_host_to_bk_switch`

---

### 3.5 cc_InstAsst_0_pub - 实例关联关系表

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
| `bk_relation_type_id` | VARCHAR | 是 | 关联类型ID（外键到cc_AsstDes） |

---

### 3.6 cc_ObjectBase_0_pub_{obj_id} - 模型实例表

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
| `bk_operate_time` | TIMESTAMP | 否 | 操作时间 |

**扩展字段**：
- 除系统字段外，还包含业务自定义字段
- 字段类型根据 `cc_ObjAttDes` 中的定义动态映射

---

## 四、字段规则

### 4.1 通用字段规则

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
   - 长度无严格限制

### 4.2 bk_inst_id 和 bk_inst_name 特殊规则

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

## 五、数据类型映射

### 5.1 SQL 类型映射

| 属性类型 | SQLite | PostgreSQL | MySQL |
|---------|--------|-----------|-------|
| `int` | INTEGER | INTEGER | INT |
| `long` | BIGINT | BIGINT | BIGINT |
| `singlechar` | VARCHAR | VARCHAR | VARCHAR |
| `shortchar` | VARCHAR | VARCHAR | VARCHAR |
| `longchar` | TEXT | TEXT | TEXT |
| `char` | VARCHAR | VARCHAR | VARCHAR |
| `text` | TEXT | TEXT | TEXT |
| `float` | FLOAT | REAL | FLOAT |
| `double` | DOUBLE | DOUBLE PRECISION | DOUBLE |
| `date` | DATE | DATE | DATE |
| `time` | TIME | TIME | TIME |
| `datetime` | TIMESTAMP | TIMESTAMP | DATETIME |
| `bool` | BOOLEAN | BOOLEAN | BOOLEAN |
| `enum` | TEXT | TEXT | TEXT |
| `enummulti` | TEXT | TEXT | TEXT |
| `list` | TEXT | TEXT | TEXT |
| `textarea` | TEXT | TEXT | TEXT |
| `objuser` | TEXT | TEXT | TEXT |
| `array` | TEXT | TEXT | TEXT |
| `object` | TEXT | TEXT | TEXT |

### 5.2 方言转换处理

使用 `sqlglot` 库处理多数据库方言转换：
```python
from sqlglot import parse_one, transpile

# 将标准 SQL 转换为特定方言
sql = transpile("SELECT * FROM table", read="sqlite", write="postgresql")
```

---

## 六、属性选项格式（Option）

### 6.1 option 字段存储规则

`option` 字段在数据库中存储为 **JSON 序列化字符串**，后端 API 会自动反序列化为对应类型返回给前端。

**存储格式**：
- 数据库存储：`'[{"id": "xxx", "name": "xxx", ...}]'`（JSON 字符串）
- API 返回：反序列化后的对象/数组

---

### 6.2 枚举类型（enum）- 单选枚举

#### Go 结构定义（原项目源码）

```go
// src/common/metadata/attribute.go
type EnumOption []EnumVal

type EnumVal struct {
    ID        string `bson:"id"           json:"id"`
    Name      string `bson:"name"         json:"name"`
    Type      string `bson:"type"         json:"type"`
    IsDefault bool   `bson:"is_default"   json:"is_default"`
}
```

#### 数据库存储格式

```json
[
    {"id": "running", "name": "运行中", "type": "text", "is_default": true},
    {"id": "stopped", "name": "已停止", "type": "text", "is_default": false},
    {"id": "maintenance", "name": "维护中", "type": "text", "is_default": false}
]
```

#### 验证规则

| 字段 | 规则 | 说明 |
|------|------|------|
| `id` | 不能为空，最大 128 Unicode 字符 | **完全支持中文** |
| `name` | 不能为空，最大 128 Unicode 字符 | **完全支持中文** |
| `type` | 必须是 "text" | 固定值 |
| `is_default` | 单选只能有 1 个为 true | 多选无此限制 |

#### 长度常量

```go
// src/common/definitions.go
AttributeOptionValueMaxLength = 128   // 单个选项ID/Name最大长度（Unicode字符）
AttributeOptionArrayMaxLength = 200  // 选项数组最大长度
```

#### 示例

```json
[
    {"id": "公网", "name": "公网", "type": "text", "is_default": false},
    {"id": "内网", "name": "内网", "type": "text", "is_default": true}
]
```

---

### 6.3 多选枚举类型（enummulti）

多选枚举与单选枚举使用相同的结构，区别在于 `is_default` 数量限制：

- **单选枚举（enum）**：只能有 1 个 `is_default: true`
- **多选枚举（enummulti）**：可以有多个 `is_default: true`（表示默认选中多个）

#### 数据库存储格式

```json
[
    {"id": "HTTP", "name": "HTTP", "type": "text", "is_default": true},
    {"id": "HTTPS", "name": "HTTPS", "type": "text", "is_default": true},
    {"id": "TCP", "name": "TCP", "type": "text", "is_default": false},
    {"id": "UDP", "name": "UDP", "type": "text", "is_default": false}
]
```

#### 示例

```json
[
    {"id": "生产环境", "name": "生产环境", "type": "text", "is_default": true},
    {"id": "测试环境", "name": "测试环境", "type": "text", "is_default": true},
    {"id": "开发环境", "name": "开发环境", "type": "text", "is_default": false}
]
```

---

### 6.4 列表类型（list）

#### Go 结构定义（原项目源码）

```go
// src/common/metadata/attribute.go
type ListOption []string
type ListOptions []string
```

#### 数据库存储格式

```json
["北京", "上海", "广州", "深圳"]
```

#### 验证规则

| 规则 | 说明 |
|------|------|
| 数组长度 | 最大 200 项 |
| 单项长度 | 最大 128 Unicode 字符 |
| 内容 | 字符串数组 |

---

### 6.5 整数范围类型（int）

#### Go 结构定义（原项目源码）

```go
// src/common/metadata/attribute.go
type IntOption struct {
    Min int64 `bson:"min" json:"min"`
    Max int64 `bson:"max" json:"max"`
}
```

#### 数据库存储格式

```json
{"min": 0, "max": 100}
```

#### 验证规则

- `min` 必须小于等于 `max`
- 支持负数

---

### 6.6 浮点数范围类型（float）

#### Go 结构定义（原项目源码）

```go
// src/common/metadata/attribute.go
type FloatOption struct {
    Min float64 `bson:"min" json:"min"`
    Max float64 `bson:"max" json:"max"`
}
```

#### 数据库存储格式

```json
{"min": 0.0, "max": 100.5}
```

---

### 6.7 表格类型（table）

#### Go 结构定义（原项目源码）

```go
// src/common/metadata/attribute.go
type TableAttributesOption struct {
    Header  []Attribute              `json:"header" bson:"header"`
    Default []map[string]interface{} `json:"default" bson:"default"`
}
```

#### 数据库存储格式

```json
{
    "header": [
        {"bk_property_id": "col1", "bk_property_name": "列1", "bk_property_type": "text"},
        {"bk_property_id": "col2", "bk_property_name": "列2", "bk_property_type": "int"}
    ],
    "default": [
        {"col1": "value1", "col2": 100}
    ]
}
```

---

### 6.8 类型汇总表

| 属性类型 | option 存储格式示例 | 是否支持中文 ID |
|---------|-------------------|----------------|
| `singlechar`（短字符） | `null`（不存储） | 不适用 |
| `shortchar`（短字符） | `null`（不存储） | 不适用 |
| `longchar`（长字符） | `null`（不存储） | 不适用 |
| `text`（文本） | `null`（不存储） | 不适用 |
| `enum`（单选枚举） | `[{"id":"x","name":"y","type":"text","is_default":false}]` | ✅ 完全支持 |
| `enummulti`（多选枚举） | `[{"id":"x","name":"y","type":"text","is_default":false}]` | ✅ 完全支持 |
| `list`（列表） | `["选项1","选项2"]` | ✅ 数组项支持中文 |
| `int`（整数范围） | `{"min":0,"max":100}` | 不适用 |
| `float`（浮点范围） | `{"min":0.0,"max":100.5}` | 不适用 |
| `table`（表格） | `{"header":[...],"default":[...]}` | ✅ 列名支持中文 |
| `bool`（布尔） | `null` 或不存储 | 不适用 |
| `date/time`（日期时间） | `null` 或不存储 | 不适用 |
| `char`（字符） | `"^[a-zA-Z]\\w*$"` | ✅ 可存储中文正则 |

---

### 6.9 数据库字段映射

| 字段名 | 存储内容 | 说明 |
|--------|---------|------|
| `option` | JSON 字符串 | 原始选项配置 |
| `bk_property_option` | JSON 字符串 | 选项配置副本（与 option 相同） |

---

## 七、与原项目对比

| 原项目 (MongoDB) | Lite项目 (SQLAlchemy) | 状态 |
|------------------|----------------------|------|
| `cc_ObjDes` | `cc_ObjDes` | ✅ 完全一致 |
| `cc_ObjAttDes` | `cc_ObjAttDes` | ✅ 完全一致 |
| `cc_AsstDes` | `cc_AsstDes` | ✅ 完全一致 |
| `cc_ObjAsst` | `cc_ObjAsst` | ✅ 完全一致 |
| `cc_InstAsst_{supplier}_pub` | `cc_InstAsst_0_pub` | ✅ 完全一致 |
| `cc_ObjectBase_{supplier}_pub_{obj}` | `cc_ObjectBase_0_pub_{obj}` | ✅ 完全一致 |
| `cc_ObjClassification` | （简化） | ⚠️ 暂未实现 |
| `cc_PropertyGroup` | （简化） | ⚠️ 暂未实现 |

---

## 八、新增模型标准步骤

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
    'bk_custom_model', 'name', '名称', 'singlechar',
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

## 九、参考文件

- **数据库引擎**：[engine.py](file:///workspace/cmdb_server_lite/app/db/engine.py)
- **数据库配置**：[settings.py](file:///workspace/cmdb_server_lite/app/config/settings.py)
- **数据库迁移工具**：[migrate.py](file:///workspace/cmdb_server_lite/app/migrate/migrate.py)
- **API服务启动**：[run.py](file:///workspace/cmdb_server_lite/run.py)
- **原项目表结构**：[tablenames.go](file:///workspace/bk-cmdb/src/common/tablenames.go)
- **原项目UI常量**：[model-constants.js](file:///workspace/bk-cmdb/src/ui/src/dictionary/model-constants.js)
- **原项目UI属性**：[property-constants.js](file:///workspace/bk-cmdb/src/ui/src/dictionary/property-constants.js)

---

## 十、原项目结构体与 MongoDB 表映射

### 10.1 Attribute 结构体与 cc_ObjAttDes 表映射

**原项目结构体定义**（来自 [attribute.go](file:///workspace/bk-cmdb/src/common/metadata/attribute.go#L106-L134)）：

```go
// Attribute attribute metadata definition
type Attribute struct {
    BizID             int64       `field:"bk_biz_id" json:"bk_biz_id" bson:"bk_biz_id" mapstructure:"bk_biz_id"`
    ID                int64       `field:"id" json:"id" bson:"id" mapstructure:"id"`
    OwnerID           string      `field:"bk_supplier_account" json:"bk_supplier_account" bson:"bk_supplier_account" mapstructure:"bk_supplier_account"`
    ObjectID          string      `field:"bk_obj_id" json:"bk_obj_id" bson:"bk_obj_id" mapstructure:"bk_obj_id"`
    PropertyID        string      `field:"bk_property_id" json:"bk_property_id" bson:"bk_property_id" mapstructure:"bk_property_id"`
    PropertyName      string      `field:"bk_property_name" json:"bk_property_name" bson:"bk_property_name" mapstructure:"bk_property_name"`
    PropertyGroup     string      `field:"bk_property_group" json:"bk_property_group" bson:"bk_property_group" mapstructure:"bk_property_group"`
    PropertyGroupName string      `field:"bk_property_group_name,ignoretomap" json:"bk_property_group_name" bson:"-" mapstructure:"bk_property_group_name"`
    PropertyIndex     int64       `field:"bk_property_index" json:"bk_property_index" bson:"bk_property_index" mapstructure:"bk_property_index"`
    Unit              string      `field:"unit" json:"unit" bson:"unit" mapstructure:"unit"`
    Placeholder       string      `field:"placeholder" json:"placeholder" bson:"placeholder" mapstructure:"placeholder"`
    IsEditable        bool        `field:"editable" json:"editable" bson:"editable" mapstructure:"editable"`
    IsPre             bool        `field:"ispre" json:"ispre" bson:"ispre" mapstructure:"ispre"`
    IsRequired        bool        `field:"isrequired" json:"isrequired" bson:"isrequired" mapstructure:"isrequired"`
    IsReadOnly        bool        `field:"isreadonly" json:"isreadonly" bson:"isreadonly" mapstructure:"isreadonly"`
    IsOnly            bool        `field:"isonly" json:"isonly" bson:"isonly" mapstructure:"isonly"`
    IsSystem          bool        `field:"bk_issystem" json:"bk_issystem" bson:"bk_issystem" mapstructure:"bk_issystem"`
    IsAPI             bool        `field:"bk_isapi" json:"bk_isapi" bson:"bk_isapi" mapstructure:"bk_isapi"`
    PropertyType      string      `field:"bk_property_type" json:"bk_property_type" bson:"bk_property_type" mapstructure:"bk_property_type"`
    Option            interface{} `field:"option" json:"option" bson:"option" mapstructure:"option"`
    Default           interface{} `field:"default" json:"default,omitempty" bson:"default" mapstructure:"default"`
    IsMultiple        *bool       `field:"ismultiple" json:"ismultiple,omitempty" bson:"ismultiple" mapstructure:"ismultiple"`
    Description       string      `field:"description" json:"description" bson:"description" mapstructure:"description"`
    TemplateID        int64       `field:"bk_template_id" json:"bk_template_id" bson:"bk_template_id" mapstructure:"bk_template_id"`
    Creator           string      `field:"creator" json:"creator" bson:"creator" mapstructure:"creator"`
    CreateTime        *Time       `json:"create_time" bson:"create_time" mapstructure:"create_time"`
    LastTime          *Time       `json:"last_time" bson:"last_time" mapstructure:"last_time"`
}
```

**对应 MongoDB 表**：`cc_ObjAttDes`（见 [tablenames.go](file:///workspace/bk-cmdb/src/common/tablenames.go#L38-L39)）

**bson 标签对照表**：

| Go 结构体字段 | bson 标签 | SQL 表字段 | 说明 |
|--------------|-----------|-----------|------|
| `BizID` | `bk_biz_id` | `bk_biz_id` | 业务ID |
| `ID` | `id` | `id` | 整数ID |
| `OwnerID` | `bk_supplier_account` | `bk_supplier_account` | 供应商账号 |
| `ObjectID` | `bk_obj_id` | `bk_obj_id` | 所属模型ID |
| `PropertyID` | `bk_property_id` | `bk_property_id` | 属性ID |
| `PropertyName` | `bk_property_name` | `bk_property_name` | 属性名称 |
| `PropertyGroup` | `bk_property_group` | `bk_property_group` | 属性分组 |
| `PropertyGroupName` | `-` | `bk_property_group_name` | 属性分组名称（不存储） |
| `PropertyIndex` | `bk_property_index` | `bk_property_index` | 属性排序索引 |
| `Unit` | `unit` | `unit` | 单位 |
| `Placeholder` | `placeholder` | `placeholder` | 占位符 |
| `IsEditable` | `editable` | `editable` | 是否可编辑 |
| `IsPre` | `ispre` | `ispre` | 是否预置属性 |
| `IsRequired` | `isrequired` | `isrequired` | 是否必填 |
| `IsReadOnly` | `isreadonly` | `isreadonly` | 是否只读 |
| `IsOnly` | `isonly` | `isonly` | 是否唯一 |
| `IsSystem` | `bk_issystem` | `bk_issystem` | 是否系统字段 |
| `IsAPI` | `bk_isapi` | `bk_isapi` | 是否API字段 |
| `PropertyType` | `bk_property_type` | `bk_property_type` | 属性类型 |
| `Option` | `option` | `option` | 选项配置 |
| `Default` | `default` | `default` | 默认值 |
| `IsMultiple` | `ismultiple` | `ismultiple` | 是否多选 |
| `Description` | `description` | `description` | 描述 |
| `TemplateID` | `bk_template_id` | `bk_template_id` | 模板ID |
| `Creator` | `creator` | `creator` | 创建者 |
| `CreateTime` | `create_time` | `create_time` | 创建时间 |
| `LastTime` | `last_time` | `last_time` | 最后修改时间 |

---

**文档维护**：本文档随代码更新，请保持同步。
- **最后更新**：2026-07-01
- **更新内容**：
  - v2.0 - 数据库架构重构，从 DuckDB 迁移到 SQLAlchemy 2.0+ + 多数据库支持
  - v2.1 - 新增属性选项格式（Option）章节，详细定义 enum/enummulti/list/int/float/table 等类型的 JSON schema 和 MongoDB 存储格式
  - v2.2 - 补充 cc_ObjDes 和 cc_ObjAttDes 表的完整字段定义，包含所有 bson 标签字段对照，新增 ismultiple 字段说明
  - v2.3 - 新增「原项目结构体与 MongoDB 表映射」章节，完整整理 Attribute 结构体所有 bson 标签对照
  - v2.4 - 统一属性类型规范，移除 `string` 类型，使用 `singlechar`/`shortchar`/`longchar`/`text` 替代，与原项目蓝鲸 CMDB 保持一致
