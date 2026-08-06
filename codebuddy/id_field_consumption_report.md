# id 字段消费排查报告（bk-cmdb-lite）

> 排查范围：所有 lite 项目（后端 `cmdb_server_lite` / 前端 `cmdb_ui_lite`）中元数据表 `id` 字段的真实消费情况。
> 重点表：`cc_ObjDes` / `cc_ObjAttDes` / `cc_ObjAsst` / `cc_AsstDes`。
> 排查目的：对照此前 `_id` 字段的"预留不消费"结论，确认 `id`（非 `_id`）是否被代码读取/使用，评估移除或改造的风险。
> 方法：使用精确正则 `(?<![a-zA-Z_])id\b` 与 `['""]id['""]` 检索，避免误命中 `bk_obj_id` / `bk_inst_id` 等子串；逐表核对写入（migrate）与读取（service / api / ui）。

---

## 0. 结论速览

| 表 | `id` 列定义 | 是否被真实消费 | 消费位置 | 结论 |
|---|---|---|---|---|
| `cc_ObjDes` | `INTEGER`（PK=`bk_obj_id`） | ❌ 否（仅写入） | 读取一律用 `bk_obj_id` | **休眠列**，等同于预留 `_id`，可保留或移除 |
| `cc_ObjAttDes` | `INTEGER`（PK=`(bk_obj_id, bk_property_id)`） | ✅ **是（负载关键）** | `instance_service.py:723/747`、`migrate.py:1789/1819/1848`、`form-multiple.vue:237` | **不可移除**，唯一性校验核心关联键 |
| `cc_ObjAsst` | `INTEGER`（PK=`bk_obj_asst_id`） | ❌ 否（仅写入） | 所有 JOIN 用 `bk_obj_asst_id` / `bk_asst_id` | **休眠列**，可保留或移除 |
| `cc_AsstDes` | `INTEGER`（PK=`bk_asst_id`） | ❌ 否（仅写入） | 所有 JOIN 用 `bk_asst_id` | **休眠列**，可保留或移除 |

> 唯一在关联路径读取 `id` 的代码是 `association_service.py:132` 的 `assoc.get('id')` —— 但那是**实例关联分表 `cc_InstAsst.id`（PK）**，用于跨分表去重，属合法使用，**与 `cc_ObjAsst`/`cc_AsstDes` 的 `id` 无关**。

---

## 1. cc_ObjDes — `id` 不被消费

**列定义（migrate.py:811）**：`id INTEGER`，主键为 `bk_obj_id`。

**写入（migrate.py）**：
- `migrate_models_data`（:983）：`id = idx + 1`（模型枚举顺序）
- `migrate_builtin_models`（:1006）：`id = model["obj_sort_number"] + 100`

**读取**：全部查询仅 `SELECT bk_obj_id FROM cc_ObjDes`（:476 / :1708 / :1774 / :1777），无任何逻辑引用 `id`。

**结论**：`cc_ObjDes.id` 为**写而不读的休眠列**。其语义与预留 `_id` 一致（仅入库、不参与业务）。如未来要精简，可移除而不影响运行；当前保留无害。

---

## 2. cc_ObjAttDes — `id` 是负载关键字段 ⚠️

**列定义（migrate.py:849）**：`id INTEGER`，主键为 `(bk_obj_id, bk_property_id)`。

**写入（migrate.py）**：
- 内置模型属性 `migrate_builtin_model_attributes`（:1018, :1039）：`attr_id = 10000` 起，逐属性 `+1`
- UI 模型属性 `migrate_attributes`（:1153, :1186/1242）：`attr_id = 1` 在模型循环**外**初始化 → **全局顺序累加**，UI 属性 `id` 跨模型唯一

**真实消费点（4 处，缺一不可）**：

| 位置 | 代码 | 作用 |
|---|---|---|
| `instance_service.py:723` | `attr_map = {attr.get('id'): attr for attr in attributes}` | 以 `cc_ObjAttDes.id` 为键建属性映射 |
| `instance_service.py:731/756` | `attr = attr_map.get(key.get('key_id'))` | 用 `cc_ObjectUnique.keys.key_id` 反查属性 |
| `migrate.py:1789/1819/1848` | `SELECT id FROM cc_ObjAttDes` → 写入 `key_id` | 播种内置唯一约束时取属性 `id` |
| `form-multiple.vue:237` | `this.properties.find((p) => p.id === key.key_id)` | 前端据 `key_id` 定位属性，隐藏唯一字段 |

**调用链（跨表强依赖）**：
```
cc_ObjectUnique.keys.key_id  ──必须等于──>  cc_ObjAttDes.id
        │                                     │
   unique.py 校验 key_id 为整数           model.py:62 属性 API 返回 id
   instance_service 反查 attr_map          (for_web 仅过滤 bk_issystem/bk_isapi，保留 id)
        │
   form-multiple.vue 前端反查唯一字段
```

**结论**：`cc_ObjAttDes.id` 与 `cc_ObjectUnique.keys.key_id` 构成**强耦合关联**，是后端唯一性校验（`check_unique` / `get_unique_attributes` / `get_object_unique_constraints`）与前端唯一约束展示的基础。**该 `id` 不可移除、不可随意变更**。

---

## 3. cc_ObjAsst / cc_AsstDes — `id` 不被消费

**列定义（migrate.py:880 / :898）**：`id INTEGER`，主键分别为 `bk_asst_id` / `bk_obj_asst_id`。

**写入（migrate.py）**：
- `cc_AsstDes`（:1525-1529）：`id = idx`（关联类型枚举顺序 1,2,3…）
- `cc_ObjAsst`（:1583-1591）：`id = idx`（对象关联枚举顺序）

**读取**：所有关联查询均以业务键 JOIN，从不使用 `id`：
- `association_service.py:52/89`：`JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id`
- `topo_service.py:138`、`relation_service.py:19-20`：同上
- `get_model_associations`（:77-92）：SELECT 显式列，未选 `id`
- `select_association_types.sql:1`：`SELECT * FROM cc_AsstDes` 虽返回 `id`，但前端用 `bk_asst_id` 标识关联类型

**前端**：UI 对关联类型/对象关联均使用 `bk_asst_id` / `bk_obj_asst_id`，无 `cc_AsstDes.id` / `cc_ObjAsst.id` 消费。

**结论**：两表 `id` 均为**写而不读的休眠列**，与预留 `_id` 同性质，可保留或移除，不影响运行。

---

## 4. 其他 `id` 消费（上下文，非元数据表）

以下 `id` 为各自表的**主键（PK）或实例级字段**，属正常业务消费，与元数据表 `id` 无关：

| 位置 | 字段来源 | 性质 |
|---|---|---|
| `instance_service.py:701` | 实例表 `id`（PK，`migrate.py:1287`） | 兜底搜索列，合法 |
| `instance_service.py:854` | `data['id'] = instance_id` | 写入实例 PK，合法 |
| `association.py:37` | `condition.get('id')`（实例查询条件） | 实例 PK，合法 |
| `model_service.py:139/152/167` | `cc_ObjectUnique.id`（PK AUTOINCREMENT） | 唯一约束记录主键，合法 |
| `association_service.py:228/245/409` | `cc_InstAsst.id`（PK） | 实例关联主键 / 跨分表去重，合法 |
| `host-list.vue:999` | `row.id`（实例行兜底） | 实例 PK 兜底，合法 |
| `general-model/index.vue:153/159` | `column.id` | 实为 `bk_property_id`（实例行键），非元数据 `id` |
| `form.vue:269` / `form-multiple.vue` 选项 | `opt.id` | 枚举选项 `id`，非元数据表 |

---

## 5. 与 `_id` 的对比（呼应此前结论）

| 维度 | `_id`（此前 Req F 结论） | `id`（本次结论） |
|---|---|---|
| 类型 | 已改为 `TEXT`（`migrate.py` 13 处） | `INTEGER` |
| 写入 | 仅入库预留，运行时不赋值 | 运行时不赋值，仅 migrate 种子写入 |
| 后端消费 | ❌ 不消费（仅白名单透传 Mongo 来源） | ⚠️ `cc_ObjAttDes.id` **被消费** |
| 前端消费 | ❌ 不消费 | ⚠️ `form-multiple.vue:237` 消费 `cc_ObjAttDes.id` |
| 风险 | 移除安全 | 仅 `cc_ObjAttDes.id` 移除会破坏唯一性 |

---

## 6. 稳定性提示（潜在脆弱点）

- `cc_ObjAttDes.id` 为**确定性全局顺序**生成（内置属性 `10000+`、UI 属性从 `1` 跨模型顺序累加），单次构建结果稳定，重跑 migrate 得到相同 `id`。
- **潜在脆弱点**：`cc_ObjectUnique.keys.key_id` 是 `cc_ObjAttDes.id` 的"快照"。若未来发生属性迁移顺序调整、模型增删导致 `id` 重排，旧 `key_id` 会指向错误属性 → **唯一性校验静默失效**（不报错但校验错乱）。
- **重构建议**（若后续要解耦）：将 `cc_ObjectUnique.keys` 的关联键由 `key_id`（属性整数 `id`）改为 `bk_property_id`（业务稳定键），即可消除对 `cc_ObjAttDes.id` 的依赖，使 `id` 与 `_id` 一样退化为纯预留列。当前版本**保持现状、保留 `id`**。

---

## 7. 处置建议

1. **保留** `cc_ObjAttDes.id` 及全部写入逻辑，禁止删除或改为非确定性生成。
2. `cc_ObjDes.id` / `cc_ObjAsst.id` / `cc_AsstDes.id` 当前为休眠列；可随 `_id` 一起视为"预留列"，但**暂不建议移除**（移除需同步改 migrate 种子，收益低）。
3. 若未来引入属性元数据变更（新增/重排模型属性），须同步重建 `cc_ObjectUnique` 的 `key_id`，避免唯一性错位。
