# bk-cmdb v3.10.50 MongoDB 字段标识体系分析报告

> 调查对象：bk-cmdb 源码（`src/` 下 Go 后端 + `src/ui` 前端）
> 调查焦点：`_id` / `id`（BKFieldID）/ `bk_inst_id`（BKInstIDField）三字段在 MongoDB 中的角色、唯一性、外键关联消费，以及 `cc_ObjAttDes` 表中 `id` 的具体用法
> 版本：release-v3.10.50

---

## 0. 字段常量速查表

| 字段 | Go 常量 | 值 | 定义位置 |
|------|---------|-----|---------|
| MongoDB 物理主键 | `_id` | `_id`（driver 自动生成 ObjectID） | MongoDB 原生，非业务定义 |
| 自增主键 | `common.BKFieldID` | `id` | `common/definitions.go:259` |
| 实例 ID | `common.BKInstIDField` | `bk_inst_id` | `common/definitions.go:368` |
| 对象 ID | `common.BKObjIDField` | `bk_obj_id` | `common/definitions.go:360` |
| 属性 ID 字段 | `metadata.AttributeFieldID` | `id` | `common/metadata/attribute.go:37` |

---

## 1. `_id` / `id` / `bk_inst_id` 三字段的角色结论

### 1.1 问题 1：`_id` 是否参与 Go / UI 的数据消费和逻辑？

**结论：基本不参与业务消费。**

- **Go 业务代码**：除 `cacheservice` 的 event/watch 变更流模块外，业务层从不读写 `_id`。
  - `cacheservice/event/watch/client.go:236,242`、`flow.go:668` 等：用 `primitive.ObjectIDFromHex` / `{"_id": ...}` 是 MongoDB **changestream 游标/resume token** 占位，与业务数据无关。
  - `cacheservice/event/bsrelation/converter.go:595`：`Oid primitive.ObjectID bson:"_id"` 是内部事件文档结构，非实例数据。
- **DAL 层默认屏蔽 `_id`**：`storage/dal/mongo/local/mongo.go:1140` 查询投影默认 `f.projection["_id"] = 0`，**除非显式 `WithObjectID=true`** 才返回 `_id`。
- **UI**：`src/ui/src` 中无任何 `_id` 消费，实例/关联/属性标识全部使用 `bk_inst_id` / `id` / `bk_obj_asst_id`。

> `_id` 仅作为 MongoDB driver 的物理行标识，业务逻辑（增删改查、关联、缓存 key）完全不依赖它。

### 1.2 问题 2：`id` 字段是否存在于主流表（实例数据、实例关联数据）？

**结论：存在但条件性——并非所有主流表都有。它是部分配置表/服务管理表的主键，但不是实例主表与实例关联主表的主键。**

| 表 | 是否含 `id`（BKFieldID） | 说明 |
|----|:---:|------|
| 实例主表 `cc_ObjectBase_*` / `cc_HostBase` | ❌ 业务代码不写 | 写入的是 `bk_inst_id`/`bk_host_id` 等 |
| 实例关联主表 `cc_InstAsst` | ❌ | 主键为 `bk_inst_id`+`bk_asst_inst_id`+`bk_obj_asst_id` |
| 实例关联**分片表** `cc_InstAsst_*` | ✅ | `GetInstIDField` 对 sharding 表返回 `BKFieldID`（`mapping.go:75`） |
| 服务/模板表 `cc_ServiceInstance`/`cc_ServiceTemplate`/`cc_ProcessTemplate` | ✅ | `GetInstIDField` 显式返回 `BKFieldID`（`mapping.go:70-73`） |
| 属性/模型描述表 `cc_ObjAttDes`/`cc_ObjDes` | ✅ | `Attribute.ID int64 bson:"id"`（`objAttDescData.go:560`） |

> 关键澄清：`save()` 实例写入路径不写 `id`（`instance_crud.go:47` 写的是 `instIDFieldName`），`id` 主要存在于服务模板/实例/进程模板等独立管理表与配置描述表。

### 1.3 问题 3：`bk_inst_id` 是否是最主要字段？ID 生成器生成哪个 id？

**结论：是——对通用普通模型的实例与实例关联，`bk_inst_id` 是最核心标识字段。ID 生成器产出的序号写入 `bk_inst_id`（通用）或内置变体（`bk_host_id` 等），而非 `_id` 或通用表的 `id`。**

**实例 ID 字段映射（`common/mapping.go` `GetInstIDField`）：**

| 对象 | 实例 ID 字段 | 常量 |
|------|------------|------|
| 通用模型（common） | `bk_inst_id` | BKInstIDField |
| 业务 | `bk_biz_id` | BKAppIDField |
| 集群 | `bk_set_id` | BKSetIDField |
| 模块 | `bk_module_id` | BKModuleIDField |
| 主机 | `bk_host_id` | BKHostIDField |
| 进程 | `bk_process_id` | BKProcIDField |
| 云区域 | `bk_cloud_id` | BKCloudIDField |
| 业务集 | `bk_biz_set_id` | BKBizSetIDField |

**ID 生成器机制（`instance_crud.go:36-47` + `mongo.go:700`）：**
```go
instTableName := common.GetInstTableName(objID, kit.SupplierAccount)
id, err := mongodb.Client().NextSequence(kit.Ctx, instTableName)  // 生成序号
instIDFieldName := common.GetInstIDField(objID)                   // 取实例ID字段名
inputParam[instIDFieldName] = id                                  // 写入 bk_inst_id / bk_host_id / ...
```
- `NextSequence` 在 **`cc_idgenerator` 集合**上以 `_id = 集合名` 为键做 `$inc: {SequenceID: 1}`，返回自增序号。
- 生成的 id 写入 `bk_inst_id`（通用）或内置变体，并**不**单独写 `id`(BKFieldID) 到实例主表。

---

## 2. `id` 字段是否作为外键关联消费

**结论：是，但有明确边界——`id`（BKFieldID）作为外键只发生在「以 `id` 为主键的独立管理表」之间（服务模板/实例/进程模板/进程实例关系/主机应用规则/模型属性等）；实例体系（`bk_inst_id`）与实例关联（`cc_InstAsst`）从不使用 `id` 跨表外键。**

### 2.1 `id` 作为外键的真实跨表引用（确认存在）

| 引用方（表） | 持有外键字段 | 目标表 | 用 `BKFieldID` 匹配 |
|------------|------------|--------|:---:|
| 服务实例 `cc_ServiceInstance` | `service_template_id` | `cc_ServiceTemplate` | ✅ `service_instance.go:298` |
| 进程实例关系 `cc_ProcessInstanceRelation` | `service_instance_id`/`process_template_id` | `cc_ServiceInstance`/`cc_ProcessTemplate` | ✅ `service_instance.go:277` |
| 主机应用规则 `cc_HostApplyRule` | 内嵌 `serviceTemplateID` | `cc_ServiceTemplate` | ✅ `rule.go:85-93` |
| 主机应用规则 | `hostAttributeIDs`/`ruleID` | `cc_ObjAttDes`/自身 | ✅ `listHostAttributes` |
| 主机转移 `transfer.go` | `serviceInstanceIDs` | `cc_ServiceInstance` | ✅ `transfer.go:543` |
| 主机标识 `identifier.go` | `serviceInstIDs` | `cc_ServiceInstance` | ✅ `identifier.go:176` |
| 进程模板 `process_template.go` | `templateID` | 自身 | ✅ |
| 服务分类 `service_category.go` | `categoryID` | 自身 | ✅ |

**典型证据（`hostapplyrule/rule.go:85-93`，用 `id` 做存在性校验——外键软约束）：**
```go
tempFilter := map[string]interface{}{
    common.BKAppIDField: bizID,
    common.BKFieldID:    serviceTemplateID,   // 引用 cc_ServiceTemplate 的主键 id
}
templateCount, _ := mongodb.Client().Table(common.BKTableNameServiceTemplate).Find(tempFilter).Count(kit.Ctx)
```

### 2.2 实例体系不使用 `id` 做外键（关键边界）

- **实例关联 `cc_InstAsst`**：`association/instance.go` 全程用 `BKInstIDField`（`bk_inst_id`）+ `BKAsstInstIDField`（`bk_asst_inst_id`）标识两端（`instance.go:42-43,111,119,131`），不碰 `BKFieldID`。
- **实例 CRUD**：`instance_crud.go:47` 写 `instIDFieldName`（bk_inst_id 等），`id` 在实例主表不被写入/引用。
- **实例关联分片表** `cc_InstAsst_*`（sharding）是唯一例外：主键为 `id`，跨表引用也走 `id`——但属关联分片表特例，非 `bk_inst_id` 实例主表。

### 2.3 外键关联判定总结

| 关联维度 | 外键字段 | 用 `id`（BKFieldID）？ |
|---------|---------|:---:|
| 服务实例 ↔ 服务模板 | `service_template_id` → `cc_ServiceTemplate.id` | ✅ 是 |
| 进程实例关系 ↔ 服务实例/进程模板 | `service_instance_id`/`process_template_id` → `.id` | ✅ 是 |
| 主机应用规则 ↔ 服务模板/属性 | 内嵌 id | ✅ 是 |
| 实例主表 ↔ 实例主表（host→module） | `bk_module_id`/`bk_inst_id` | ❌ 否 |
| 实例关联 `cc_InstAsst` 两端 | `bk_inst_id`+`bk_asst_inst_id` | ❌ 否 |

---

## 3. 实例体系集合表中是否物理存在 `id` 字段

**结论：不存在。实例主表（`cc_ObjectBase_*`/`cc_HostBase` 等）与实例关联主表（`cc_InstAsst`）在 MongoDB 物理集合里没有 `id`（BKFieldID）字段。**

### 3.1 四层证据

1. **Go 写入层不写 `id`**：`instance_crud.go:36-51` 只写入 `bk_inst_id`/变体 + `bk_obj_id` + `bk_supplier_account` + 时间戳 + 业务属性，无 `inputParam[common.BKFieldID]`。
2. **DAL 层不自动注入 `id`**：`mongo.go:473-490` 的 `Insert` 原样 `InsertMany(rows)`，无自增主键自动补。
3. **索引定义层无 `id`**：
   - 含 `"id"` 索引的表：均为主键是 `id` 的配置/服务管理表（`objdes`/`objattdes`/`objclassification`/`objasst`/`objectunique`/`propertygroup`/`asstdes`/`auditlog`/`dynamicgroup`/`hostapplyrule`/`processtemplate`/`servicecategory`/`servicetemplateattr`/`serviceinstance`）。
   - 实例相关：
     - `objectbasemapping.go:34` → 索引用 `common.BKInstIDField`（`bk_inst_id`），非 `id`。
     - 实例主表索引（`createtable.go:59-63`）仅 `bk_host_id`/`bk_host_name`/`bk_host_innerip`/`bk_host_outerip`，无 `id`。
     - 实例关联表结构用 `bk_inst_id`+`bk_asst_inst_id`+`bk_obj_asst_id`（`association.go:132,238`），索引文件无 `id`。
4. **返回结构体不含 `id`**：实例映射（`common/metadata/inst.go`）字段全为 `bk_biz_id`/`bk_set_id`/`bk_module_id`/`bk_parent_id`/`bk_inst_id`，无 `ID int64 bson:"id"`；查询走 `mapstr.MapStr` 动态文档。

### 3.2 对比表（含 `id` vs 不含 `id`）

| 集合类型 | 代表表 | 含 `id`？ | 主键字段 |
|---------|--------|:---:|---------|
| 模型/属性配置表 | `cc_ObjDes`/`cc_ObjAttDes`/`cc_ObjAsst` | ✅ | `id` |
| 服务编排表 | `cc_ServiceTemplate`/`cc_ServiceInstance`/`cc_ProcessTemplate` | ✅ | `id` |
| 规则/审计/动态分组 | `cc_HostApplyRule`/`cc_AuditLog`/`cc_DynamicGroup` | ✅ | `id` |
| **实例主表** | `cc_ObjectBase_*`/`cc_HostBase` | ❌ | `bk_inst_id`/变体 |
| **实例关联主表** | `cc_InstAsst` | ❌ | `bk_inst_id`+`bk_asst_inst_id` |
| 实例关联分片表 | `cc_InstAsst_*` | ✅ | `id`（分片特例） |
| 实例映射表 | `cc_ObjectBaseMapping` | ❌ | `bk_inst_id` |

---

## 4. `cc_ObjAttDes` 中 `id` 字段的具体使用与唯一性

**结论：`cc_ObjAttDes` 的 `id` 是这张属性描述表的「全局唯一主键」，在 Go 与 UI 中均作为属性的唯一定位标识被重度消费；MongoDB 层对其建有 `unique` 唯一索引。**

### 4.1 定义与值来源

- 结构体：`Attribute.ID int64 \`bson:"id"\``（`common/metadata/attribute.go:85`、`objAttDescData.go:560`）。
- 常量：`metadata.AttributeFieldID = "id"`（`common/metadata/attribute.go:37`）。
- 值来源：由 `cc_idgenerator` 的 `NextSequence` 自增生成（sequenceName = `cc_ObjAttDes`）。

### 4.2 是否唯一字段？（是）

**MongoDB 唯一索引**（`common/index/collections/objattdes.go` `deprecatedObjAttDesIndexes`）：
```go
{ Name: "idx_unique_Id", Keys: bson.D{{"id", 1}}, Unique: true }
```
**写入层幂等 upsert**（`addPresetObjects.go:76`）：以 `"id"` 为 upsert 冲突键。

> 并存两组唯一约束：`id`（绝对主键，全局唯一）+ `bk_obj_id + bk_property_id + bk_biz_id`（业务唯一组合，`idx_unique_objID_propertyID_bizID`）。

### 4.3 Go 中 `id` 消费方式

| 操作 | 代码位置 | 用法 |
|------|---------|------|
| 按 id 校验属性存在 | `attribute.go:214` | `attrCond = {BKFieldID: id, bk_obj_id, bk_biz_id}` → `Find().Count()` |
| 排除自身做索引冲突检查 | `attribute.go:251` | `incCond = {BKFieldID: {$ne: id}, ...}` |
| 查询回填属性 ID | `attribute_curd.go:78` | `attribute.ID = int64(id)` |
| 批量收集属性 ID | `attribute_curd.go:299,368,511` | `attrMap[objID] = append(..., attr.ID)` |
| 更新属性索引 | `attribute.go:164` | `ID: uint64(existsAttr.ID)` 回传 |

### 4.4 UI 中 `id` 消费方式

- **属性编辑提交**：`field-detail/index.vue:362` → `id: this.field.id` 带入请求体。
- **属性展示**：`field-view.vue:145-147` 显示 `${item.name}(${item.id})`。
- **后端 API 路径锚定**：`object_attribute.go:150` `id, _ := strconv.ParseInt(ctx.Request.PathParameter("id"), ...)` → 更新/删除路径 `/update/objectattr/{id}/{bk_obj_id}`，`id` 即 `cc_ObjAttDes.id`，传给 coreservice 用 `common.BKFieldID: id` 精准命中。

---

## 5. 总体结论速览

| 维度 | `_id` | `id`（BKFieldID） | `bk_inst_id` |
|------|-------|-------------------|--------------|
| 物理来源 | MongoDB driver 自动 | `cc_idgenerator` 自增 | `cc_idgenerator` 自增 |
| 是否业务主键 | ❌ 否 | ✅（配置/服务表） | ✅（实例/关联表） |
| 唯一索引 | 原生 | ✅（如 `cc_ObjAttDes.idx_unique_Id`） | ✅（业务组合约束） |
| Go 业务消费 | 仅 cacheservice event | ✅ 管理表 CRUD/外键 | ✅ 实例主标识 |
| UI 消费 | ❌ | ✅ 属性/模板管理 | ✅ 实例详情/关联 |
| 实例主表存在 | ✅（driver） | ❌ | ✅ |
| 实例关联主表存在 | ✅（driver） | ❌ | ✅ |

**一句话总结**：bk-cmdb 把「配置项实例」与「平台资源管理」拆分为两套 ID 体系——实例主线用 `bk_inst_id`（由 `cc_idgenerator` 生成、无 `id` 字段、无 `_id` 业务消费），而配置/服务管理表用 `id`（BKFieldID，全局唯一、可作外键、UI/Go 重度消费）；`_id` 仅作 MongoDB 物理行标识，被 DAL 默认投影排除。

---

## 附：关键源码定位索引

| 主题 | 文件:行 |
|------|---------|
| `_id` 默认投影排除 | `storage/dal/mongo/local/mongo.go:1140` |
| `id` 生成器（`$inc` 自增） | `storage/dal/mongo/local/mongo.go:700-711` |
| 实例写入（`bk_inst_id` 填充） | `source_controller/coreservice/core/instances/instance_crud.go:36-47` |
| 实例 ID 字段映射 | `common/mapping.go:45`（GetInstIDField） |
| 实例关联用 `bk_inst_id` 外键 | `source_controller/coreservice/core/association/instance.go:42-43,111,119` |
| 服务实例→模板用 `id` 外键 | `source_controller/coreservice/core/process/service_instance.go:277,298` |
| 主机规则→模板用 `id` 外键 | `source_controller/coreservice/core/hostapplyrule/rule.go:85-93` |
| `cc_ObjAttDes` 唯一索引 | `common/index/collections/objattdes.go`（idx_unique_Id） |
| `cc_ObjAttDes` 按 id 更新 | `scene_server/topo_server/service/object_attribute.go:150` |
| 实例表无 id 索引 | `common/index/collections/objectbasemapping.go:34` |
