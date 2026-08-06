# bk-cmdb host 实例 / 模型描述 / 属性描述 涉及表分析

> 版本: release-v3.10.41
> 核心结论: **host 实例只存在于 `cc_HostBase` 一张表,绝对不会落到通用 Object 实例分片表 `cc_ObjectBase_{supplier}_pub_host`。** 模型描述在 `cc_ObjDes`、属性描述在 `cc_ObjAttDes`(两张表是所有模型共用的"字典表",靠 `bk_obj_id="host"` 区分)。

---

## 1. 结论先行

| 问题 | 结论 |
| --- | --- |
| host 实例存在几张表? | **仅 1 张**: `cc_HostBase`(主线条专用表) |
| 是否也存在于通用 Object inst 表 `cc_ObjectBase_{supplier}_pub_host`? | **否**。该表根本不会被创建/写入(见 §3) |
| host 模型描述在哪? | `cc_ObjDes`(`bk_obj_id="host"`) |
| host 属性描述在哪? | `cc_ObjAttDes`(`bk_obj_id="host"`) |
| 与 host 相关的"链路/挂载"表有哪些? | `cc_ModuleHostConfig`、`cc_PlatBase`、`cc_Process`、`cc_ServiceInstance`、`cc_ProcessInstanceRelation`、`cc_HostApplyRule`、`cc_HostFavourite`、`cc_HostLock` |

> 容易把"host 实例"和"host 在主线拓扑中的挂载关系"混淆。host 实例本体(`bk_host_id` 及其全部属性)只在 `cc_HostBase`;它与模块、云区域的**关系**分别在 `cc_ModuleHostConfig` 与 `cc_PlatBase` 中,这些不是实例主表。

---

## 2. 涉及表清单

### 2.1 三类核心表(回答本题)

| 类别 | 表名(常量) | 源码常量 | 作用 | 是否共用 |
| --- | --- | --- | --- | --- |
| host 实例 | `cc_HostBase` | `BKTableNameBaseHost` | 存放主机实例本体(`bk_host_id`、`bk_host_innerip`、`bk_host_outerip`、`bk_cloud_id`、`bk_asset_id`、`bk_os_*` 等全部主机属性) | **仅 host 专用** |
| host 模型描述 | `cc_ObjDes` | `BKTableNameObjDes` | 模型元信息(`bk_obj_id="host"`、`bk_obj_name`、`bk_classification_id`、`bk_supplier_account`、`bk_ispaused` 等) | **所有模型共用**,按 `bk_obj_id` 区分 |
| host 属性描述 | `cc_ObjAttDes` | `BKTableNameObjAttDes` | 属性元信息(`bk_obj_id="host"`、`bk_property_id`、`bk_property_name`、`bk_property_type`、`bk_property_group`、`bk_isapi` 等) | **所有模型共用**,按 `bk_obj_id` 区分 |

三张表的常量定义位置: `src/common/tablenames.go:35/29/46`

```go
BKTableNameObjDes    = "cc_ObjDes"      // L29 模型描述
BKTableNameObjAttDes = "cc_ObjAttDes"   // L35 属性描述
BKTableNameBaseHost  = "cc_HostBase"    // L46 host 实例
```

### 2.2 host 实例相关的"链路/挂载"表(非实例本体,但常被误认)

| 表名(常量) | 源码常量 | 作用 | 与 host 的关系 |
| --- | --- | --- | --- |
| `cc_ModuleHostConfig` | `BKTableNameModuleHostConfig` | 主机↔模块挂载关系表 | 记录 `bk_host_id` + `bk_module_id` + `bk_supplier_account`,一条主机可挂多模块 |
| `cc_PlatBase` | `BKTableNameBasePlat` | 云区域(管控区域)表 | `cc_HostBase.bk_cloud_id` 外键指向此表的 `bk_cloud_id` |
| `cc_Process` | `BKTableNameBaseProcess` | 进程实例表 | 进程挂载在主机上(`bk_host_id`) |
| `cc_ServiceInstance` | `BKTableNameServiceInstance` | 服务实例 | 服务实例绑定主机(`bk_host_id`) |
| `cc_ProcessInstanceRelation` | `BKTableNameProcessInstanceRelation` | 进程实例关系 | 关联进程与主机/模块/服务实例 |
| `cc_HostApplyRule` | `BKTableNameHostApplyRule` | 主机属性自动应用规则 | 基于主机属性做自动赋值 |
| `cc_HostFavourite` | `BKTableNameHostFavorite` | 主机收藏 | 用户收藏的主机列表 |
| `cc_HostLock` | `BKTableNameHostLock` | 主机锁 | 防止并发操作同一主机 |

> 注意: 上表里的 `cc_Process`、`cc_PlatBase` 也是主线条"专用 Base 表",与 `cc_HostBase` 同属内建对象(`BKInnerObjIDProc="proc"`、`BKInnerObjIDPlat="plat"`),同样**不进**通用分片表。

---

## 3. 为什么 host 实例不在通用 Object inst 表

### 3.1 内建对象走专用表,自定义对象才走分片表

路由核心在 `src/common/tablenames.go:214` 的 `GetInstTableName`:

```go
func GetInstTableName(objID, supplierAccount string) string {
    switch objID {
    case BKInnerObjIDApp:    return BKTableNameBaseApp      // cc_ApplicationBase
    case BKInnerObjIDBizSet: return BKTableNameBaseBizSet   // cc_BizSetBase
    case BKInnerObjIDSet:    return BKTableNameBaseSet      // cc_SetBase
    case BKInnerObjIDModule: return BKTableNameBaseModule   // cc_ModuleBase
    case BKInnerObjIDHost:   return BKTableNameBaseHost     // ★ cc_HostBase
    case BKInnerObjIDProc:   return BKTableNameBaseProcess  // cc_Process
    case BKInnerObjIDPlat:   return BKTableNameBasePlat     // cc_PlatBase
    default:
        return GetObjectInstTableName(objID, supplierAccount) // cc_ObjectBase_{supplier}_pub_{objID}
    }
}
```

- `host` 命中 `case BKInnerObjIDHost`(常量 `BKInnerObjIDHost = "host"`,定义于 `src/common/definitions.go:113`),直接返回 `cc_HostBase`。
- 只有落到 `default` 分支时,才会生成 `cc_ObjectBase_{supplier}_pub_{objID}` 这种**通用分片表**。host 永远不会进入该分支。
- 全代码库检索 `pub_host` / `GetObjectInstTableName(...host)` **零命中**,证明没有任何逻辑会把 host 实例写入通用分片表。

### 3.2 通用分片表只在"新建自定义模型"时创建

通用实例分片表由 `createObjectShardingTables`(`src/source_controller/coreservice/core/model/model_crud.go:188`)创建,仅由 `CreateModelTables`(`model_tables.go:22`)调用,而 `CreateModelTables` 只在**新增自定义模型**流程中触发。

host 是**内建主线条模型**,在系统初始化时注册(走 `cc_ObjDes` 内建数据 + 专用 `cc_HostBase` 表),**不**经过"新建模型"流程,因此:
- 不存在 `cc_ObjectBase_0_pub_host` 这张表;
- 即便手工在 `cc_ObjDes` 里看到 `bk_obj_id="host"`,它的实例也始终读写 `cc_HostBase`。

### 3.3 host 在代码里被"特殊对待"的证据

`src/storage/dal/mongo/local/mongo.go` 对 `cc_HostBase` 有专门分支:

- `tryArchiveDeletedDoc`(L634-657): `case common.BKTableNameBaseHost:` 被纳入软删除归档白名单(host 删除时写 `cc_DelArchive`)。
- `validHostType`(L1184-1193): 仅当 `collection == BKTableNameBaseHost` 时,把主机特殊字段(`bk_host_innerip`/`bk_host_outerip` 等数组 ↔ 字符串)做转换——这种定制逻辑也反向证明 host 是独立表,而非走通用实例表。

---

## 4. host 实例与主线拓扑的关系(为什么容易误以为它在别的表)

主线拓扑链: **业务(biz) → 集群(set) → 模块(module) → 主机(host)**。

- `biz/set/module` 通过实例上的 `bk_parent_id` 字段逐级挂载(存在于各自的 Base 表)。
- `host` 是**叶子节点**,它**不通过 `bk_parent_id` 挂到 module**,而是通过 `cc_ModuleHostConfig`(主机-模块关系表)挂载。
- `cc_HostBase` 中的 `bk_cloud_id` 通过 `cc_PlatBase` 关联云区域。

所以一份完整的"主机"数据 = `cc_HostBase`(本体) + `cc_ModuleHostConfig`(挂哪些模块) + `cc_PlatBase`(在哪个云区域)。三者都是独立表,**主机实例本体只有 `cc_HostBase` 一份**。

### 4.1 业务拓扑-模块视图的主机列表,拼接了哪些其他列?

进入"业务拓扑"点击某模块,右侧主机列表并不是只展示 `cc_HostBase` 的字段,而是由 **`host_server` 的 `SearchHost` 流程**(`src/scene_server/host_server/logics/hostsearch.go`)在返回时**额外 join 了主线拓扑的列**。核心函数链路:

```
SearchHost (hostsearch.go:33)
  ├─ SearchHostByConds   → 按拓扑/主机条件初筛 hostID
  └─ FillTopologyData    → 把拓扑列拼回每一行 (hostsearch.go:209)
       ├─ GetHostRelations → 读 cc_ModuleHostConfig,取 bk_app_id / bk_set_id / bk_module_id / bk_host_id
       ├─ fetchTopoAppCacheInfo    → 读 cc_ApplicationBase (业务)
       ├─ fetchTopoSetCacheInfo    → 读 cc_SetBase          (集群/set)
       ├─ fetchTopoModuleCacheInfo → 读 cc_ModuleBase       (模块)
       └─ fetchHostCloudCacheInfo  → 读 cc_PlatBase         (云区域)
```

最终每一行返回的是一个 map,键为各对象 ID,值里**额外拼接**的拓扑列如下:

| 拼接键 | 来源表 | 拼接进来的属性列 | 说明 |
| --- | --- | --- | --- |
| `host`(值本身) | `cc_HostBase` | `bk_host_id`、`bk_host_innerip`、`bk_host_outerip`、`bk_asset_id`、`bk_os_*` 等全部主机属性 | 主机本体;其中 `bk_cloud_id` 被改写为 `[{bk_inst_id, bk_inst_name, bk_obj_id:"plat"}]` 结构(见下) |
| `bk_biz` | `cc_ApplicationBase` | `bk_biz_id`、`bk_biz_name` | 业务列;一台主机可属于多个业务时返回数组 |
| `bk_set` | `cc_SetBase` | `bk_set_id`、`bk_set_name`(可加 `bk_set_template_id` 等) | 集群/set 列;额外写入合成字段 `TopSetName = "业务名##集群名"` |
| `bk_module` | `cc_ModuleBase` | `bk_module_id`、`bk_module_name`(可加 `bk_service_template_id` 等) | 模块列;额外写入合成字段 `TopModuleName = "业务名##集群名##模块名"` |
| `host.bk_cloud_id` | `cc_PlatBase` | `bk_cloud_id` + `bk_cloud_name` | 云区域:由 `fillHostCloudInfo` 把 `bk_cloud_id` 关联 `cc_PlatBase` 的 `bk_cloud_name`,转成 `InstNameAsst` 数组挂回 host |

> 关键代码点:
> - 关系来源 `cc_ModuleHostConfig`(`FillTopologyData` L215-217 固定 `Fields: bk_app_id / bk_set_id / bk_module_id / bk_host_id`)。
> - 拼接合成链 `TopSetName`/`TopModuleName`(`hostsearch.go:411`、`443`,分隔符常量 `SplitFlag = "##"`)。
> - 云区域改写 `fillHostCloudInfo`(`hostsearch.go:303`),`bk_cloud_name` 取自 `cc_PlatBase`。

### 4.2 拼接规则小结

- **"其他列"都来自主机本体之外的 4 张表**:`cc_ApplicationBase`(业务)、`cc_SetBase`(集群)、`cc_ModuleBase`(模块)、`cc_PlatBase`(云区域),外加关系表 `cc_ModuleHostConfig` 提供的挂载 ID。
- 这些列**不是** host 实例表 `cc_HostBase` 的字段,而是查询期**联表拼接(join)**出来的展示列,后台返回的每个主机对象是一个 `{host, bk_biz, bk_set, bk_module}` 的嵌套结构。
- 一台主机可同时挂在多个模块/集群/业务下,因此 `bk_set`、`bk_module`、`bk_biz` 都是**数组**,前端再按需展开成「业务 / 集群 / 模块」列展示。
- 由此也能再次印证:**主机实例本体永远只有 `cc_HostBase` 一份**,业务拓扑里看到的「集群」「模块」等列只是基于 `cc_ModuleHostConfig` 关系做的联表展示,并不在 host 实例表里多存一份。

---

## 5. 模型描述 / 属性描述表的关键字段

### 5.1 `cc_ObjDes`(模型描述,host 行示例)

| 字段 | 说明 |
| --- | --- |
| `bk_obj_id` | 固定 `"host"`(内建对象 ID) |
| `bk_obj_name` | 显示名,如「主机」 |
| `bk_classification_id` | 模型分组,host 归属主机类分组 |
| `bk_supplier_account` | 开发商账号(隔离维度) |
| `bk_ispaused` / `bk_ismanage` | 是否停用 / 是否可管理 |

### 5.2 `cc_ObjAttDes`(属性描述,host 属性行示例)

| 字段 | 说明 |
| --- | --- |
| `bk_obj_id` | `"host"`(关联到哪个模型) |
| `bk_property_id` | 属性 ID,如 `bk_host_innerip`、`bk_cloud_id` |
| `bk_property_name` | 属性名 |
| `bk_property_type` | 类型:`singlechar`/`int`/`enum`/`foreignkey`/`time` 等 |
| `bk_property_group` | 属性分组 ID(对应 `cc_PropertyGroup`) |
| `bk_isapi` / `bk_ismultiple` | 是否 API 字段 / 是否多值 |

> 所有模型的属性都写进**同一张** `cc_ObjAttDes`,查询时以 `bk_obj_id="host"` 过滤。因此"host 属性描述"并不独占一张表,而是 `cc_ObjAttDes` 里的一部分行。

---

## 6. 易混淆点澄清(回答"是否存在于2个表"的来源)

| 误解 | 事实 |
| --- | --- |
| host 实例既在 `cc_HostBase` 又在 `cc_ObjectBase_*_pub_host` | **不存在**通用分片表这一说,host 只进 `cc_HostBase` |
| `cc_ObjDes` / `cc_ObjAttDes` 是 host 专用表 | 否,是**全模型共用字典表**,靠 `bk_obj_id` 区分;host 只是其中 `bk_obj_id="host"` 的行 |
| `cc_ModuleHostConfig` 里也有 host,所以 host 在两表 | `cc_ModuleHostConfig` 只存"挂载关系"(host↔module),**不存 host 属性本体**,不等于实例表 |
| 内建对象也会生成 `cc_ObjectBase_*_pub_*` | 只有**自定义模型**才会;内建主线条对象(biz/set/module/host/proc/plat)全部走专用 Base 表 |

---

## 7. 代码索引(便于二次核对)

| 主题 | 位置 |
| --- | --- |
| 全部表名常量 | `src/common/tablenames.go`(L20-108) |
| 实例表路由(专用 vs 通用分片) | `src/common/tablenames.go:214` `GetInstTableName` |
| 通用分片表名构造 | `src/common/tablenames.go:182` `GetObjectInstTableName` |
| 内建对象 ID 常量 | `src/common/definitions.go:104-113`(`BKInnerObjIDHost="host"`) |
| 通用分片表创建(仅自定义模型) | `src/source_controller/coreservice/core/model/model_crud.go:188` |
| host 实例读写样例 | `src/source_controller/coreservice/service/host.go:155/189/202` |
| 模块主机列表拼接逻辑(联表列) | `src/scene_server/host_server/logics/hostsearch.go:33` `SearchHost` / `:209` `FillTopologyData` |
| 业务/集群/模块/云区域 缓存拉取 | `hostsearch.go:454` `fetchTopoAppCacheInfo` / `:471` `fetchTopoSetCacheInfo` / `:488` `fetchTopoModuleCacheInfo` / `:320` `fetchHostCloudCacheInfo` |
| 合成链 TopSetName/TopModuleName | `hostsearch.go:411/443`(分隔符 `##` 常量 L254 `SplitFlag`) |
| 云区域列改写 bk_cloud_id→bk_cloud_name | `hostsearch.go:303` `fillHostCloudInfo` |
| host 特殊字段转换 | `src/storage/dal/mongo/local/mongo.go:1184` `validHostType` |
| host 删除归档白名单 | `src/storage/dal/mongo/local/mongo.go:634` `tryArchiveDeletedDoc` |
| 属性描述读写 | `src/source_controller/coreservice/core/model/attribute_curd.go`(多处 `BKTableNameObjAttDes`) |
| 模型描述读写 | `src/source_controller/coreservice/core/model/model_crud.go`(`BKTableNameObjDes`) |
