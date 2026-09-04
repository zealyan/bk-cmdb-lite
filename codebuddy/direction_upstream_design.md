# direction 在原项目（bk-cmdb 上游）的消费与功能设计

> 源码位置：`/workspace/bk-cmdb`（Go 后端 + Vue 前端）
> 核查时间：2026-09-03 22:00 ~ 22:15
> 结论：**direction 在上游只被前端「拓扑连线箭头渲染」消费，后端全程透传不校验**；lite 的实现与上游值域一致，且额外做了上游没有的严格校验

## 1. 类型与值域定义

`src/common/metadata/association.go:388-400`

```go
type AssociationDirection string

const (
	NoneDirection        AssociationDirection = "none"
	DestinationToSource  AssociationDirection = "src_to_dest"   // 注意：名字与值相反
	SourceToDestination  AssociationDirection = "dest_to_src"   // 注意：名字与值相反
	Bidirectional        AssociationDirection = "bidirectional"
)
```

**上游常量命名错位（重要）**：`DestinationToSource` 的值是 `src_to_dest`，`SourceToDestination` 的值是 `dest_to_src` —— 名字与取值语义相反。这是上游的历史遗留，只影响代码可读性，不影响行为：因为**所有预置数据和 UI 表单写的都是字符串字面量或直接用该常量**，存库结果都是 `"src_to_dest"`。

lite 侧在 `app/definitions.py` 与 `app/migrate/seeds.py` 注释中已记录这一点，并统一引用 `ASST_DIRECTION_SRC_TO_DEST` 常量，避开了该陷阱。

所属结构 `AssociationKind`（`association.go:403-421`）：

| 字段 | tag | 说明 |
|---|---|---|
| `SourceToDestinationNote` | `src_des` | 源→目标描述，拓扑建链时展示 |
| `DestinationToSourceNote` | `dest_des` | 目标→源描述，拓扑建链时展示 |
| `Direction` | `direction` | 两端关联方向 |
| `IsPre` | `ispre` | 是否预置 |

## 2. 功能设计：direction 到底用来干什么

direction 的**唯一业务语义是「控制拓扑图上连线的箭头形态」**，即决定这条关联在图上是否有箭头、箭头指向谁。四个值的渲染规则（cytoscape 样式表）：

| direction | 源端箭头 | 目标端箭头 | 语义 |
|---|---|---|---|
| `none` | none | none | 无方向，对等连线 |
| `src_to_dest` | none | `triangle-backcurve` | 源指向目标（默认） |
| `dest_to_src` | `triangle-backcurve` | none | 目标指向源（反向） |
| `bidirectional` | `triangle-backcurve` | `triangle-backcurve` | 双向 |

## 3. 消费点清单（全部位置）

### 3.1 前端：拓扑连线箭头（真正的业务消费）

| 文件 | 位置 | 作用 |
|---|---|---|
| `src/ui/src/components/instance/association/graphics-config.js` | 89-116 | **样式表最完整**，四个值全覆盖（`none` / `bidirectional` / `src_to_dest` / `dest_to_src`） |
| `src/ui/src/components/instance/association/index.vue` | 78-88、113-121 | `getDirection()` 计算 `arrow`，写入 cytoscape edge 的 `data.direction` |
| `src/ui/src/views/model-topology/index.new.vue` | 472-485、746-757、1136-1143 | 模型拓扑图；`getAsstDetail()` 取 `asst.direction` 注入 edge，样式表只覆盖 `none`/`bidirectional`（其余走默认 `target-arrow-shape`） |

`index.vue:87` 的箭头翻转逻辑（实例关联图）：

```js
arrow: !instance.target && define.direction === 'src_to_dest'
  ? 'src_to_dest'
  : define.direction
```

即：**当前实例作为源且方向为 `src_to_dest` → 正向箭头；作为目标时直接沿用原始 direction**（由样式表翻转表现）。

### 3.2 前端：`src_des` / `dest_des` 的方向语义文案

direction 决定了「读哪一个描述字段」，UI 按当前实例是源还是目标二选一：

| 文件 | 位置 | 用法 |
|---|---|---|
| `views/host-details/children/association-create.vue` | 451 | `` `${isSource ? type.src_des : type.dest_des}-${model.bk_obj_name}` `` |
| `views/host-details/children/association-list-table.vue` | 159-161 | `title = ${desc}-${model.bk_obj_name}` |
| `components/model-instance/relation/create.vue` | 431 | 同上 |
| `components/model-instance/relation/list-table.vue` | 159 | 同上 |
| `components/instance/association/index.vue` | 86 | `label: !instance.target ? define.src_des : define.dest_des` |

**lite 完全复刻了这套设计**（`instance-association/index.vue:233/238`、`association-create.vue:333/341`），且额外补了空值回退链（上游部分位置无回退）。

### 3.3 前端：关联类型管理表单（direction 的编辑入口）

`src/ui/src/views/model-association/_detail.vue:82-103` —— **三选项单选**：

| 选项 | value |
|---|---|
| 有，源指向目标 | `src_to_dest` |
| 无方向 | `none` |
| 双向 | `bidirectional` |

**注意**：上游表单**不提供 `dest_to_src`**，尽管样式表支持它。因此 `dest_to_src` 在上游属于「数据层可用、UI 不可创建」的值（只能由 API/数据库直接写入）。lite 的 CLI/API 值域是完整的四个值，比上游 UI 更全。

预置类型（`ispre=true`）的名称与描述、方向全部**只读**（`:disabled="isReadOnly || isEdit && relation.ispre"`），lite 侧同样有预置禁改禁删保护。

### 3.4 前端：列表展示

`views/model-association/index.vue:64-65` —— 关联类型列表直接列 `src_des`（源->目标描述）、`dest_des`（目标->源描述）两列。
`views/model-manage/.../model-import-editor.vue:126-133` —— 模型导入导出时比对 `src_des`/`dest_des` 冲突。

### 3.5 后端：全程透传，无值域校验

| 位置 | 行为 |
|---|---|
| `src/scene_server/topo_server/service/association.go:710-715`（更新） | `"direction": request.Direction` 直接写库，无校验 |
| 同上 `:650-689`（创建） | `ctx.DecodeInto` 后直接透传 coreservice，无校验 |
| `src/source_controller/coreservice/core/association/kind.go:35-48` | 只校验 `bk_asst_id` 唯一性，**不校验 direction** |
| `kind_test.go` / `instance_test.go` 多处 | 单元测试直接写 `Direction = "test"`，佐证上游允许任意字符串入库 |

## 4. 预置数据（上游）

唯一的预置定义位置：`src/scene_server/admin_server/upgrader/history/x18.10.30.01/association.go:88-155`

| bk_asst_id | src_des | dest_des（上游文案） | direction | ispre |
|---|---|---|---|---|
| `belong` | 属于 | 包含 | `src_to_dest` | true |
| `group` | 组成 | 组成于 | `src_to_dest` | true |
| `bk_mainline` | 组成 | 组成于 | `src_to_dest` | true |
| `run` | 运行于 | 运行 | `src_to_dest` | true |
| `connect` | 上联 | 下联 | `src_to_dest` | true |
| `default` | 关联 | 被关联 | `src_to_dest` | true |

- **6 个预置全部 `src_to_dest`**，与 lite 一致（lite 另有 `install`，为 SLB 演示数据自加）；
- 上游预置数据的 `bk_asst_name` **为空字符串**（UI 回退显示 `bk_asst_id`），lite 补齐了中文名（属于/分组/主线/运行/连接/默认）—— 属刻意改进，seeds.py 注释已说明；
- 上游**没有 `SourceToDestination`（`dest_to_src`）的任何预置数据**，全项目搜不到该常量的使用点（除定义处）。

## 5. 与 lite 实现的差异对照

| 维度 | 上游 bk-cmdb | bk-cmdb-lite | 判定 |
|---|---|---|---|
| 值域 | `none/src_to_dest/dest_to_src/bidirectional` | 同 | 一致 |
| 预置 6 类型 direction | 全部 `src_to_dest` | 同 | 一致 |
| 后端值域校验 | **无**（任意字符串可入库） | 有（严格值域 + 历史脏值归一） | lite 更严，属改进 |
| 前端拓扑箭头消费 | 有（模型拓扑图 + 实例关联图） | **无**（lite 无拓扑图视图） | lite 尚未实现该消费 |
| `src_des/dest_des` 方向文案 | 有（5 处列表/创建/拓扑） | 有（同构设计 + 空值回退） | 一致，lite 兜底更稳 |
| 关联类型管理 UI 表单 | 有（三选项单选，`dest_to_src` 不可选） | 无 UI，仅 CLI/API（四值全可选） | 互补 |
| `ispre` 预置保护 | 只读 + 禁删 | 同（另加 CLI 双重保护） | 一致 |
| 常量命名 | 名字与值错位 | 引用常量，注释说明 | lite 规避了陷阱 |

## 6. 建议

1. **lite 无需为 direction 补 UI 表单**（除非要上拓扑图），当前字段已可被 API/CLI 正确管理，UI 侧因不消费方向值域而无兼容风险；
2. 若后续要在 lite 实现拓扑图/关联图，可直接复用上游 `graphics-config.js` 的四值样式表 —— lite 的值域已经完整支持，包括上游 UI 都造不出的 `dest_to_src`；
3. lite 的严格值域校验是对上游的改进，建议保留：上游允许 `"test"` 这类值入库，会让箭头渲染落到「默认样式」，属于静默降级。
