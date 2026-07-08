# bk-cmdb v3.10.41 主线拓扑（Mainline）与业务拓扑树 数据分析报告

> 基于 `TencentBlueKing/bk-cmdb` 源码 `release-v3.10.41` 分析
> 分析范围：主线拓扑、业务拓扑树所涉及的 MongoDB 表结构与数据，覆盖 **业务 / 集群 / 模块 / 主机** 及其关联表（含对"系统"歧义的澄清）

---

## 1. 背景与核心结论

bk-cmdb 的**业务拓扑树**是指一个业务（biz）下 `集群(set) → 模块(module) → 主机(host)` 的层级结构。其中真正构成"**主线（mainline）**"的，只有内置的三大内置模型：**业务 / 集群 / 模块**。

代码层面的几个**关键事实**（与直觉不同，务必注意）：

| 维度 | 结论 |
|------|------|
| 主线父子关系靠什么字段？ | 每个实例记录上的 **`bk_parent_id`** 字段，指向父实例的 `bk_*_id`，**不是** `cc_InstAsst` 表 |
| 主线"模型链"（biz→set→module）定义在哪？ | **`cc_ObjAsst`** 关联定义表，关联类型 `bk_asst_id = "bk_mainline"` |
| 主机如何挂到拓扑？ | 主机 **不**进入主线实例链；主机通过 **`cc_ModuleHostConfig`**（主机-模块关系表）挂载到模块 |
| 主机与云区域（平台）的关系？ | 通过主机实例字段 **`bk_cloud_id`** 关联到 `cc_BasePlat`（云区域表） |
| 非主线实例关联（如交换机→主机） | 才使用 **`cc_InstAsst`** 表，关联类型为自定义（如 `connect` 等） |
| 拓扑可视化布局 | **`cc_TopoGraphics`** 表，保存每个节点（scope+node_type+obj+inst）在页面上的坐标 |

> **一句话总结**：业务拓扑树 = `cc_ApplicationBase`/`cc_SetBase`/`cc_ModuleBase` 三张实例表通过 `bk_parent_id` 串成主线实例链 + `cc_ModuleHostConfig` 把主机挂到模块 + `cc_ObjAsst`(bk_mainline) 描述这条链"长什么样"。

---

## 2. 涉及的数据表总览

| 表名（collection） | 角色 | 关键字段 | 是否主线核心 |
|--------------------|------|----------|--------------|
| `cc_ApplicationBase` | 业务实例表 | bk_biz_id, bk_biz_name, default, bk_supplier_account | ✅ 主线根 |
| `cc_SetBase` | 集群实例表 | bk_set_id, bk_parent_id, bk_biz_id, bk_supplier_account | ✅ 主线 |
| `cc_ModuleBase` | 模块实例表 | bk_module_id, bk_parent_id, bk_set_id, bk_biz_id, bk_supplier_account | ✅ 主线叶 |
| `cc_HostBase` | 主机实例表 | bk_host_id, bk_host_innerip, bk_host_outerip, bk_cloud_id, bk_supplier_account | ⚠️ 通过模块挂载 |
| `cc_ModuleHostConfig` | 主机-模块挂载关系 | bk_biz_id, bk_host_id, bk_module_id, bk_set_id | ✅ 关联桥 |
| `cc_ObjAsst` | 关联模型定义（含主线链） | bk_obj_id, bk_asst_obj_id, bk_asst_id, bk_supplier_account | ✅ 模型链定义 |
| `cc_TopoGraphics` | 拓扑节点布局 | scope_type, scope_id, node_type, bk_obj_id, bk_inst_id, position | ⚠️ 展示用 |
| `cc_InstAsst` | 非主线实例关联 | bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id | ❌ 非主线 |
| `cc_System` | 版本/元数据 | version 等 | ⚠️ 迁移版本锚点 |
| `cc_BasePlat` | 云区域（平台） | bk_cloud_id, bk_supplier_account | 主机归属云 |

> 业务集（Business Set / `bk_biz_set`）在 v3.10.41 是业务之上的逻辑分组，不属于默认主线实例链；其数据落在通用实例表 `cc_ObjectBase_{supplier}_pub_bizset` 中。下文第 7 节专门澄清"系统"的歧义。

---

## 3. 各表 Schema 详解

所有索引定义源自 `src/scene_server/admin_server/upgrader/history/v3.0.8/createtable.go`（`createTable` 在初始化时按 `tables` 映射建表并建索引，已存在则幂等跳过）。

### 3.1 `cc_ApplicationBase`（业务 biz）

业务是主线拓扑的**根节点**，没有 `bk_parent_id`（没有父级）。

**实例字段（`metadata/inst.go` `BizInst` 及通用属性）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_biz_id` | int64 | 业务 ID（主键，由 `cc_IDgenerator` 生成） |
| `bk_biz_name` | string | 业务名称 |
| `default` | int | 是否为默认业务（内置"资源池"业务的 default=1） |
| `bk_supplier_account` | string | 供应商账户（租户隔离键，默认 `"0"`） |
| 其它业务属性 | — | 由 `cc_ObjAttDes` 中 `bk_obj_id="bk_biz"` 的属性动态决定 |

**索引：**

```text
{ bk_biz_id: 1 }
{ bk_biz_name: 1 }
{ default: 1 }
```

> 注：内置"资源池（空闲机池）"也是一个业务实例（`default=1`），所有未分配主机挂在它的默认集群/模块下。

### 3.2 `cc_SetBase`（集群 set）

集群挂在某个业务下，通过 `bk_parent_id` 指向业务（`bk_biz_id`），是主线的**第一层**。

**实例字段（`metadata/inst.go` `SetInst`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_set_id` | int64 | 集群 ID（主键） |
| `bk_set_name` | string | 集群名称 |
| `bk_parent_id` | int64 | **父节点 ID（= 所属业务的 `bk_biz_id`）** |
| `bk_biz_id` | int64 | 所属业务 ID（冗余，便于查询） |
| `bk_supplier_account` | string | 供应商账户 |
| `bk_service_status` | string | 服务状态（如 enabled/disabled） |
| `bk_set_env` | string | 环境（如 test/prod） |
| `set_template_id` | int64 | 集群模板 ID（使用模板时为模板生成） |

**索引：**

```text
{ bk_set_id: 1 }
{ bk_parent_id: 1 }
{ bk_biz_id: 1 }
{ bk_supplier_account: 1 }
{ bk_set_name: 1 }
```

### 3.3 `cc_ModuleBase`（模块 module）

模块挂在集群下，通过 `bk_parent_id` 指向集群（`bk_set_id`），是主线的**叶子层**（主机不直接挂在模块之上再往下的主线）。

**实例字段（`metadata/inst.go` `ModuleInst`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_module_id` | int64 | 模块 ID（主键） |
| `bk_module_name` | string | 模块名称 |
| `bk_parent_id` | int64 | **父节点 ID（= 所属集群的 `bk_set_id`）** |
| `bk_set_id` | int64 | 所属集群 ID（冗余） |
| `bk_biz_id` | int64 | 所属业务 ID（冗余） |
| `bk_supplier_account` | string | 供应商账户 |
| `default` | int | 是否为默认模块（空闲机/故障机/待回收模块等） |
| `service_category_id` | int64 | 服务分类 ID |
| `service_template_id` | int64 | 服务模板 ID（使用模板时为模板生成） |
| `set_template_id` | int64 | 所属集群模板 ID（冗余） |
| `host_apply_enabled` | bool | 是否开启主机属性自动应用 |

**索引：**

```text
{ bk_module_id: 1 }
{ bk_module_name: 1 }
{ default: 1 }
{ bk_biz_id: 1 }
{ bk_supplier_account: 1 }
{ bk_set_id: 1 }
{ bk_parent_id: 1 }
```

### 3.4 `cc_HostBase`（主机 host）

主机本身**不在主线实例链里**，而是通用实例。它的"拓扑位置"完全由 `cc_ModuleHostConfig` 决定。

**实例字段（无独立强类型 struct，按通用实例 + `cc_ObjAttDes` 动态属性）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_host_id` | int64 | 主机 ID（主键） |
| `bk_host_name` | string | 主机名称 |
| `bk_host_innerip` | string | 内网 IP |
| `bk_host_outerip` | string | 外网 IP |
| `bk_cloud_id` | int64 | **云区域 ID，关联到 `cc_BasePlat`** |
| `bk_supplier_account` | string | 供应商账户 |
| 其它主机属性 | — | 由 `cc_ObjAttDes` 中 `bk_obj_id="host"` 的属性决定 |

**索引：**

```text
{ bk_host_id: 1 }
{ bk_host_name: 1 }
{ bk_host_innerip: 1 }
{ bk_host_outerip: 1 }
```

### 3.5 `cc_ModuleHostConfig`（主机-模块挂载关系）

这是把"主机"接入业务拓扑树的**唯一桥梁表**（多对多：一个主机可在多个模块，一个模块有多台主机）。

**字段（`metadata/hostcontroller.go` `ModuleHostConfigParams` 对应存储结构）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_biz_id` | int64 | 业务 ID |
| `bk_host_id` | int64 | 主机 ID |
| `bk_module_id` | int64 | 模块 ID |
| `bk_set_id` | int64 | 集群 ID（冗余，便于按集群查主机） |
| `bk_supplier_account` | string | 供应商账户 |

**索引：**

```text
{ bk_biz_id: 1 }
{ bk_host_id: 1 }
{ bk_module_id: 1 }
{ bk_set_id: 1 }
```

> 代码 `mainline_association.go` 的 `getDistinctHostCount()` 即通过对 `cc_ModuleHostConfig` 按 `bk_module_id` 做 `distinct(bk_host_id)` 来统计每个模块的 host 数。

### 3.6 `cc_ObjAsst`（关联模型定义 + 主线模型链）

这是**最关键的一张"元表"**。它既定义普通模型间关联，也定义**主线模型链**。

**字段（`metadata/association.go` `MainlineAssociation` / `InstAsst` 相关）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_obj_id` | string | 源模型 ID（子节点，如 set/module/host） |
| `bk_asst_obj_id` | string | 目标模型 ID（父节点，如 app/set/module） |
| `bk_asst_id` | string | 关联类型。**主线链固定为 `"bk_mainline"`** |
| `bk_obj_asst_id` | string | 关联唯一标识 |
| `bk_supplier_account` | string | 供应商账户 |

**索引：**

```text
{ bk_obj_id: 1 }
{ bk_asst_obj_id: 1 }
{ bk_supplier_account: 1 }
```

**主线模型链的 seed 数据（`addPresetObjects.go` `getAddAsstData`）：**

```json
[
  { "bk_obj_id": "set",     "bk_asst_obj_id": "app",  "bk_asst_id": "bk_mainline" },
  { "bk_obj_id": "module",  "bk_asst_obj_id": "set",  "bk_asst_id": "bk_mainline" },
  { "bk_obj_id": "host",    "bk_asst_obj_id": "module","bk_asst_id": "bk_mainline" },
  { "bk_obj_id": "host",    "bk_asst_obj_id": "plat", "bk_asst_id": "bk_mainline" }
]
```

> 遍历时（`SearchMainlineAssociationInstTopo`）：
> 1. 查 `cc_ObjAsst` 中 `bk_asst_id="bk_mainline"` 的全部记录；
> 2. 构建 `child→parent` 映射：`set→app`、`module→set`、`host→module`；
> 3. **排除 host** 作为主线实例节点（host 不进入 `bk_parent_id` 链），host 只作为属性挂在 module 上；
> 4. 由此得到主线模型顺序：**app → set → module**。

### 3.7 `cc_TopoGraphics`（拓扑节点布局）

保存拓扑图中每个节点的页面坐标与图标，**纯展示层数据**，不影响业务逻辑。

**字段（`metadata/graphic.go` `TopoGraphics`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `scope_type` | string | 作用域类型（如 biz） |
| `scope_id` | int64 | 作用域 ID（业务 ID） |
| `node_type` | string | 节点类型（biz/set/module/host 等） |
| `bk_obj_id` | string | 模型 ID |
| `bk_inst_id` | int64 | 实例 ID |
| `ispre` | bool | 是否为上游节点 |
| `node_name` | string | 节点显示名 |
| `position` | object | `{x, y}` 坐标 |
| `ext` | object | 扩展信息 |
| `bk_obj_icon` | string | 图标 |
| `bk_supplier_account` | string | 供应商账户 |
| `assts` | array | 关联节点列表 |

**索引（唯一）：**

```text
{ scope_type: 1, scope_id: 1, node_type: 1, bk_obj_id: 1, bk_inst_id: 1 }  UNIQUE
```

### 3.8 `cc_InstAsst`（非主线实例关联）

**注意**：这张表**不是**业务主线拓扑的数据来源。它只保存**非主线**的实例级关联，例如"交换机连接主机"（自定义 `connect` 关联）、自定义模型之间的关联实例。

**字段（`metadata/association.go` `InstAsst`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `bk_obj_id` | string | 源实例所属模型 |
| `bk_inst_id` | int64 | 源实例 ID |
| `bk_asst_obj_id` | string | 目标实例所属模型 |
| `bk_asst_inst_id` | int64 | 目标实例 ID |
| `bk_obj_asst_id` | string | 使用的关联定义 ID |
| `bk_asst_id` | string | 关联类型（非 `bk_mainline`） |
| `bk_biz_id` | int64 | 业务 ID |
| `bk_supplier_account` | string | 供应商账户 |

**索引：**

```text
{ bk_obj_id: 1, bk_inst_id: 1 }
```

### 3.9 `cc_System`（版本/元数据）

`createtable.go` 中为空索引（`{}`）。该表记录**当前库的迁移版本**（如 `version: "v3.10.41"`），是 `init_db` / `admin_server` 升级链路（Upgrader Chain）判断"已执行到哪个版本"的锚点。数据迁移前后务必校对它。

---

## 4. 实例父子关系：`bk_parent_id` 串联机制

主线拓扑**不**靠关系表反查，而是**每个子实例直接存储父实例 ID**。下面是一棵真实拓扑树的实例记录示例：

```json
// 业务（根，无父）
{ "_id": "...", "bk_biz_id": 2, "bk_biz_name": "蓝鲸测试业务", "default": 0, "bk_supplier_account": "0" }

// 集群（父 = 业务 bk_biz_id=2）
{ "_id": "...", "bk_set_id": 10, "bk_set_name": "广州一区", "bk_parent_id": 2, "bk_biz_id": 2, "bk_supplier_account": "0" }

// 模块（父 = 集群 bk_set_id=10）
{ "_id": "...", "bk_module_id": 100, "bk_module_name": "web", "bk_parent_id": 10, "bk_set_id": 10, "bk_biz_id": 2, "bk_supplier_account": "0", "default": 0 }

// 主机（不进主线链，靠 ModuleHostConfig 挂载）
{ "_id": "...", "bk_host_id": 1001, "bk_host_name": "host-01", "bk_host_innerip": "10.0.0.1", "bk_cloud_id": 0, "bk_supplier_account": "0" }

// 主机-模块挂载关系
{ "bk_biz_id": 2, "bk_host_id": 1001, "bk_module_id": 100, "bk_set_id": 10, "bk_supplier_account": "0" }
```

**查询所属路径的算法**（`buildTopoInstRst`，`mainline_association.go`）：

1. 从业务 `bk_biz_id` 出发，查 `cc_SetBase` 中 `bk_parent_id = bk_biz_id` 的集群；
2. 对每个集群，查 `cc_ModuleBase` 中 `bk_parent_id = bk_set_id` 的模块；
3. 对每个模块，查 `cc_ModuleHostConfig` 中 `bk_module_id = module` 的 `bk_host_id` 列表，再去 `cc_HostBase` 取主机详情；
4. 逐层拼成 `CommonInstTopo`（含 `Children[]`）返回。

> 主线实例表的通用唯一索引见 `common/index/instance.go`：
> - 普通实例：`{bk_obj_id:1}`、`{bk_supplier_account:1, bk_obj_id:1}`、`{bk_inst_id:1, bk_supplier_account:1}`、`{bk_inst_id:1}`(unique)
> - **主线实例唯一约束** `MainLineInstanceUniqueIndex`：`{bk_parent_id:1, bk_inst_name:1}` 带 `PartialFilterExpression`（仅在主线模型上生效），保证同一父节点下实例名不重复。

---

## 5. 主线模型链如何定义与遍历

主线"长什么样"完全由 `cc_ObjAsst` 中 `bk_asst_id="bk_mainline"` 的记录决定，因此**支持自定义层级**：可以在 biz 和 set 之间插入自定义主线模型（如"园区/region"），方法是往 `cc_ObjAsst` 插入对应的 `bk_mainline` 关联，并在相应实例表写入 `bk_parent_id` 链。

遍历代码逻辑（`SearchMainlineAssociationInstTopo`，`mainline_association.go:239`）：

```go
// 1. 查主线模型关联
mainlineAsst := db.Table(cc_ObjAsst).Find({bk_asst_id: "bk_mainline"})
// 2. 构建 child→parent 映射
mainlineObjectChildMap[asst.AsstObjID] = asst.ObjectID
// 例: set→app, module→set, host→module
// 3. 排除 host 作为主线节点，得到 [app, set, module]
// 4. 逐级向下查询实例，组装成拓扑树
```

> 自定义主线模型（非内置 biz/set/module）的**实例数据不落在固定表**，而是落在按供应商分片的通用实例表：
> `cc_ObjectBase_{supplier}_pub_{objID}`（见 `common/tablenames.go` `GetObjectInstTableName`）。
> 内置模型（biz/set/module/host/proc/plat）才路由到 `cc_ApplicationBase`/`cc_SetBase`/`cc_ModuleBase`/`cc_HostBase` 等固定表（`IsInnerMainlineModel()` / `IsInnerModel()` 判断）。

---

## 6. 业务拓扑树查询流程（端到端）

| 步骤 | 函数 | 动作 |
|------|------|------|
| 1 | `SearchMainlineAssociationInstTopo` | 读 `cc_ObjAsst` 的 `bk_mainline`，得到模型链 `app→set→module` |
| 2 | `SetMainlineInstAssociation` | 为**每个父实例**创建子实例，写 `bk_parent_id=父id`、`bk_biz_id=父.bk_biz_id`（证明主线靠 `bk_parent_id` 连接） |
| 3 | `buildTopoInstRst` | 从业务 ID 出发，按 `bk_parent_id $in [...]` 逐级下钻，读取 `bk_inst_id/bk_inst_name/default/bk_parent_id/bk_biz_id` 等字段 |
| 4 | `getDistinctHostCount` / `getSetRelationModule` | 通过 `cc_ModuleHostConfig`、`cc_ModuleBase` 统计每个模块的 host 数量 |
| 5 | 组装 `SearchTopoResult{ Data: []*CommonInstTopo }` | 返回带 `Children[]` 的嵌套树 |
| 6 | `cc_TopoGraphics` | 前端按节点坐标渲染（不影响数据） |

返回结构（`metadata/toposerver.go`）：

- `CommonInstTopo`：`InstNameAsst` + `Count`（host 数）+ `Children[]`
- `CommonInstTopoV2`：`Prev`/`Next`/`Curr` 三段式
- `SetTopo`：`Set map` + `ModuleTopos []*ModuleTopo`
- `ModuleTopo`：`Module map` + `Hosts []map`

---

## 7. "系统"概念澄清

你列出的拓扑层级里有"**系统**"，但 **v3.10.41 默认主线里并不存在名为"系统"的内置模型**。在 cmdb 语境下，"系统"通常指以下两种之一，文档必须澄清：

| 可能含义 | 实际对应 | 说明 |
|----------|----------|------|
| **业务集（Business Set / `bk_biz_set`）** | 通用实例表 `cc_ObjectBase_{supplier}_pub_bizset` | 位于业务**之上**的逻辑分组，用于跨业务权限/视图管理，不属于默认主线实例链 |
| **云区域/平台（`plat`）** | `cc_BasePlat`（`bk_cloud_id`） | 主机通过 `bk_cloud_id` 归属的"云平台"，在 `cc_ObjAsst` 的 `bk_mainline` 中以 `host→plat` 表示 |
| **系统内置元数据** | `cc_System` | 仅存版本号，非拓扑节点 |

> 如果业务上需要在 biz 与 set 之间插入自定义"系统/区域/园区"等层级，按第 5 节方法把该模型加入 `bk_mainline` 链即可，cmdb 原生支持这种扩展。

---

## 8. 供应商账户（ownerID）与拓扑隔离 — 回答"ownerid=1 如何创建独立业务拓扑"

bk-cmdb 用 **`bk_supplier_account`（供应商账户）** 做租户隔离。源码 `definitions.go`：`BKDefaultOwnerID="0"`、`BKSuperOwnerID="superadmin"`。

**查询过滤逻辑（`SetQueryOwner`）：**

| 当前 ownerID | 查询结果过滤 |
|--------------|--------------|
| `"0"`（默认供应商） | 只查 `bk_supplier_account = "0"` 的数据 |
| `"1"`（另一租户） | 同时可见 `["0", "1"]`（见 `SetQueryOwner` 的 owner 列表拼接逻辑） |
| `"superadmin"` | **不过滤**，可见全部租户数据 |

据此，**ownerID=1 的租户创建自己独立业务拓扑**的做法：

1. **初始化隔离**：在 `init_db` / `admin_server migrate` 时，`addPresetObjects` 会按 `ownerID` 参数写入主线链与内置模型。ownerID=1 需要走一次自己的初始化（传入 `bk_supplier_account=1`），使 `cc_ObjAsst` 的主线链、`cc_ApplicationBase` 等表都带上 `bk_supplier_account="1"` 的记录。

2. **建独立业务**：通过业务接口创建 `bk_biz_id` 新业务，记录带 `bk_supplier_account="1"`。由于查询时 owner=1 能看到 `["0","1"]`，但**写入与归属**均以 `bk_supplier_account="1"` 标记，数据逻辑上独立。

3. **建集群/模块**：在 owner=1 的业务下创建 set/module，实例记录 `bk_parent_id` 链、`bk_biz_id`、`bk_supplier_account="1"` 一应俱全，与 owner=0 的业务互不串。

4. **挂主机**：往 `cc_ModuleHostConfig` 写 `(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account="1")`，主机本身在其 `cc_HostBase` 记录也带 `bk_supplier_account="1"`。

> ⚠️ **重要限制**：ownerID=1 的查询会**包含** ownerID=0 的数据（见上表）。若要求**强物理隔离**（owner=1 完全看不到 owner=0），需要：
> - 在 `SetQueryOwner` 逻辑层做定制；或
> - 直接部署**独立 MongoDB 实例 / 独立库**，从存储层彻底隔离（推荐用于多租户生产环境）。

---

## 9. 通用数据迁移思路（基于上述表关系）

要从 A 环境迁移一套业务拓扑到 B 环境，按以下顺序操作（与 `init_db` 的初始化顺序一致，保证父子依赖）：

| 顺序 | 操作 | 涉及表 | 注意 |
|------|------|--------|------|
| 1 | 迁移模型定义 | `cc_ObjDes`, `cc_ObjAttDes`, `cc_ObjClassification`, `cc_ObjAsst` | 先确保主线链 `bk_mainline` 存在 |
| 2 | 迁移业务 | `cc_ApplicationBase` | 用 `cc_IDgenerator` 重新分配 `bk_biz_id` 避免冲突 |
| 3 | 迁移集群 | `cc_SetBase` | 写 `bk_parent_id=新bk_biz_id`、`bk_biz_id` 同步更新 |
| 4 | 迁移模块 | `cc_ModuleBase` | 写 `bk_parent_id=新bk_set_id`、`bk_set_id` 同步 |
| 5 | 迁移主机 | `cc_HostBase` | 重新分配 `bk_host_id`，注意 `bk_cloud_id` 对应的 `cc_BasePlat` 也需存在 |
| 6 | 重建挂载 | `cc_ModuleHostConfig` | 用**新的** `bk_host_id`/`bk_module_id`/`bk_set_id`/`bk_biz_id` 重写 |
| 7 | 迁移非主线关联 | `cc_InstAsst` | 如交换机→主机等自定义关联 |
| 8 | 迁移布局 | `cc_TopoGraphics` | 纯展示，可后补 |
| 9 | 校验版本锚 | `cc_System` | 确认目标库版本 ≥ 源库，必要时走 `admin_server` 升级链路 |

**关键原则**：
- **先父后子**：biz → set → module → host → modulehostconfig，严格遵循 `bk_parent_id` 依赖。
- **ID 重映射**：跨库迁移必须维护 `旧ID→新ID` 映射表，所有 `bk_parent_id`/`bk_*_id`/`bk_host_id` 引用同步替换。
- **主线链不迁移实例关系**：主线拓扑关系**不存在 `cc_InstAsst`**，只靠 `bk_parent_id` 字段；切勿误把主线关系当成 `cc_InstAsst` 数据去迁移。
- **供应商隔离**：迁移时保持 `bk_supplier_account` 一致；跨租户迁移需在 `SetQueryOwner` 层或存储层处理可见性。

---

## 10. 关键代码定位参考

| 内容 | 文件 |
|------|------|
| 各表索引建表定义 | `src/scene_server/admin_server/upgrader/history/v3.0.8/createtable.go` |
| 主线模型链 seed（bk_mainline） | `src/scene_server/admin_server/upgrader/history/v3.0.8/addPresetObjects.go` `getAddAsstData` |
| 主线实例关联构建（bk_parent_id） | `src/scene_server/topo_server/logics/inst/mainline_association.go` `SetMainlineInstAssociation` |
| 主线模型链遍历 | 同上 `SearchMainlineAssociationInstTopo`（line ~239） |
| 拓扑树组装 | 同上 `buildTopoInstRst`（line ~304） |
| 主机数统计 | 同上 `getDistinctHostCount`（line ~945） |
| 实例 struct 定义 | `src/common/metadata/inst.go`（`BizInst`/`SetInst`/`ModuleInst`/`MainlineInstInfo`） |
| 关联 struct 定义 | `src/common/metadata/association.go`（`MainlineAssociation`/`InstAsst`/`MainlineObjectTopo`） |
| 内置模型判断 | `src/common/mapping.go`（`IsInnerModel`/`IsInnerMainlineModel`）、`src/common/metadata/object.go`（`IsCommon`） |
| 实例索引 | `src/common/index/instance.go`（`MainLineInstanceUniqueIndex`） |
| 表名路由 | `src/common/tablenames.go`（`GetObjectInstTableName` / `GetInstTableName`） |
| 关联类型常量 | `src/common/definitions.go`（`AssociationKindMainline="bk_mainline"`、`BKParentIDField="bk_parent_id"`） |
| 返回结构 | `src/common/metadata/toposerver.go`（`CommonInstTopo`/`SetTopo`/`ModuleTopo`）、`graphic.go`（`TopoGraphics`） |

---

> 本文档聚焦"主线拓扑 / 业务拓扑树"所涉及的数据表与 schema。若需进一步分析某张表的真实生产数据样例、或编写实际的迁移脚本，可基于第 9 节的顺序表继续展开。
