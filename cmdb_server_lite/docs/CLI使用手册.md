# CMDB-Lite CLI 使用手册（含示例 / 步骤 / 测试参考）

> 配套文档：`CLI工具设计文档.md`（设计约束、退出码、事务纪律）。
> 适用范围：`app/cli` 子工程（`python3 -m app.cli.cmdb`）。本手册同时可作为**简易测试参考**——每节示例均标注预期退出码与预期现象，文末附测试矩阵 checklist。

---

## 1. 运行环境与前置条件

| 项 | 说明 |
| --- | --- |
| 语言 | Python 3.11 |
| 调用方式 | 在项目根目录（`cmdb_server_lite/`）执行：`python3 -m app.cli.cmdb <子命令> [全局选项] [子选项]` |
| 数据库 | SQLite。**目标库必须已执行迁移**（含 `cc_ObjDes` / `cc_ObjAttDes` / `cc_PropertyGroup` / `cc_ObjClassification` 等表）。CLI 仅自动补建 `cc_ObjectUnique` 与 `cc_ImportBatch` 两张表。 |
| 推荐测试用法 | 拷贝一份已迁移库作为沙箱：`cp cmdb_dev.db /tmp/cli_test.db`，随后所有命令加 `--db /tmp/cli_test.db`，避免污染开发库。 |
| 供应商账号 | 固定为 `0`（lite 不支持多租户），无需配置。 |

### 1.1 全局选项

所有子命令前/后均可使用：

| 选项 | 说明 |
| --- | --- |
| `--db PATH` | 指定 SQLite 文件路径；省略则使用配置中的 `cmdb_dev.db`。 |
| `--env ENV` | 环境：`default` / `development` / `testing` / `production`（默认 `development`）。 |
| `--dry-run` | 仅打印将执行的 SQL / 计划，不落库。可用于安全预演。 |
| `--json` | 以 JSON 输出结果（`--db` 无关）。 |
| `--yes` / `-y` | 跳过危险操作的二次确认（目前仅 `model delete` 需要）。 |

> 错误一律输出到 **stderr**；成功结果（摘要 / 查询结果）输出到 **stdout**。脚本判定成败请依赖**退出码**，而非从 stdout 解析错误体。

### 1.2 退出码速查

| 码 | 含义 | 典型触发 |
| --- | --- | --- |
| `0` | 成功 | 正常完成；实例导入存在行级拒绝但整体对账通过时也返回 0 |
| `1` | 通用错误 / 对账不一致 | SQL 执行失败、约束冲突、整批中断（`--strict`）、分类/模型/属性导入存在失败行 |
| `2` | 参数错误 / 预检失败 | 非法标识符、表头缺必填列、未知列、`match_cols` 不在表头、`scaffold spec` 缺必填字段 |
| `3` | 依赖缺失 | 模型不存在（建属性/实例前）、分类不存在（建模型前）、实例表不存在 |
| `4` | 已存在且 `on_dup=error` | 重复创建分类 / 模型 / 属性且 `--on-duplicate error` |
| `5` | 数据库不可达 / 被锁定 | `database is locked`（后端占用连接时） |

---

## 2. 命令参考

### 2.1 classification（模型分类）

#### `classification create` — 新建单个分类
```
cmdb classification create --bk_classification_id <id> --bk_classification_name <名称> \
    [--bk_classification_icon <图标>] [--ispre true|false] \
    [--classification_index <int>] [--on-duplicate error|skip|overwrite]
```
| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--bk_classification_id` | 是 | — | 分类 ID（**不受 C1 白名单约束**，但作为值写入） |
| `--bk_classification_name` | 是 | — | 分类名称 |
| `--bk_classification_icon` | 否 | `icon-cc-default` | 图标 |
| `--ispre` | 否 | `false` | 是否预置 |
| `--classification_index` | 否 | `0` | **分类排序序号**（整数；升序，越小越靠前）。对应 `cc_ObjClassification.classification_index`，资源目录页按 `ORDER BY classification_index, id` 渲染。也接受别名 `--index`（兼容旧写法） |
| `--on-duplicate` | 否 | `error` | 已存在时：`error` 报错退 4 / `skip` 跳过 / `overwrite` 覆盖 |

> **排序说明**：资源目录页（前端）不二次排序，直接按后端 `cc_ObjClassification` 的 `ORDER BY classification_index, id` 顺序渲染分类。因此**分类间的先后完全由 `classification_index` 决定**——不指定时默认 `0`，与建表顺序（`id`）一致；要置顶给负/小值，要置底给大值。

示例：
```bash
cmdb classification create --bk_classification_id bk_application --bk_classification_name 应用系统
# 预期：退出 0，输出 “分类 bk_application: create”
```

#### `classification import` — 批量导入分类（CSV）
```
cmdb classification import --csv <文件> [--encoding utf-8-sig] [--delimiter ,] \
    [--atomic|--no-atomic] [--strict] [--on-duplicate overwrite]
```
CSV 表头（支持中文别名）：`bk_classification_id`(分类id/分类ID)、`bk_classification_name`(分类名称)、`bk_classification_icon`(图标)、`ispre`(是否预置)、`classification_index`(排序序号/排序/index/索引/sort_index)。必填：`bk_classification_id`、`bk_classification_name`；`classification_index` 缺列/空值/非法值统一回退 `0`。
> 单行坏值（如 `ispre=maybe`）会被**行级拒绝**（计入失败、不回滚整批）；加 `--strict` 则整批中断退 1。

示例：
```bash
cat > /tmp/cls.csv <<'EOF'
bk_classification_id,bk_classification_name,bk_classification_icon,ispre
bk_edge_net,边界网络,icon-cc-network,false
EOF
cmdb classification import --csv /tmp/cls.csv
# 预期：退出 0（无失败行），输出 “分类导入：新增 1 …”
```

### 2.2 model（模型）

#### `model create` — 新建模型（含默认分组 + 4 系统属性 + 实例分表 + 默认唯一约束）
```
cmdb model create --bk_obj_id <id> --bk_obj_name <名称> --bk_classification_id <分类id> \
    [--bk_obj_icon <图标>] [--ispre bool] [--obj_sort_number <int>] \
    [--with-system-props|--no-with-system-props] [--with-tables|--no-with-tables] \
    [--unique-by <属性id>] [--on-duplicate error|skip|overwrite] [--dry-run]
```
| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--bk_obj_id` | 是 | — | 模型 ID（**C1 白名单** `^[a-z][a-z0-9_]*$`，非法退 2） |
| `--bk_obj_name` | 是 | — | 模型名称 |
| `--bk_classification_id` | 是 | — | 所属分类（须已存在，否则退 3） |
| `--with-system-props` | 否 | `true` | 是否预置 4 系统属性 |
| `--with-tables` | 否 | `true` | 是否建实例分表 + 关联分表 + 默认唯一约束 |
| `--unique-by` | 否 | `bk_inst_name` | 默认唯一约束键属性 |
| `--on-duplicate` | 否 | `error` | 已存在时策略 |

示例：
```bash
cmdb model create --bk_obj_id bk_app_system --bk_obj_name 应用系统 --bk_classification_id bk_application
# 预期：退出 0；自动建 cc_ObjectBase_0_pub_bk_app_system / cc_InstAsst_0_pub_bk_app_system
#      并向 cc_ObjectUnique 写入以 bk_inst_name 为键的唯一约束
```

#### `model import` — 批量导入模型（CSV）
表头：`bk_obj_id`(模型id/模型ID)、`bk_obj_name`(模型名称)、`bk_classification_id`(所属分类/分类id/分类ID)、`bk_obj_icon`(模型图标/图标)、`ispre`(是否预置)、`bk_ishidden`(是否隐藏)、`bk_ispaused`(是否停用)、`obj_sort_number`(排序号/排序)。必填：前三项。其余选项同 `model create`（含 `--with-tables`/`--unique-by`）。
> 单行坏值（如 `obj_sort_number=abc`）行级拒绝；`--strict` 整批中断退 1。

#### `model show` / `model list` / `model delete`
```bash
cmdb model show  --bk_obj_id bk_app_system      # 查看模型 / 分组 / 属性（退出 0）
cmdb model list                                # 列出全部模型（退出 0）
cmdb model delete --bk_obj_id bk_app_system --yes   # 危险操作，需 --yes；删元数据+两张分表（退出 0）
cmdb model delete --bk_obj_id bk_app_system --dry-run   # 仅打印将删除的对象，不落库
```
> 不存在的模型 → 退 3；不加 `--yes` → 退 2（“删除模型为危险操作，请加 --yes 确认”）。

### 2.3 attribute（属性）

#### `attribute create` — 新建单个属性（并 ALTER 实例表加列）
```
cmdb attribute create --bk_obj_id <模型id> --bk_property_id <属性id> --bk_property_name <名称> \
    --bk_property_type <类型> [--bk_property_group default] [--bk_group_name <分组显示名>] \
    [--isrequired bool] [--editable bool] \
    [--bk_ishidden|--bk_isapi|--bk_issystem|--ispre|--ismultiple bool] [--bk_property_index <int>] \
    [--option <JSON>] [--placeholder <文本>] [--unit <文本>] [--on-duplicate error|skip|overwrite]
```
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--bk_obj_id` | 是 | 所属模型（须存在，否则退 3） |
| `--bk_property_id` | 是 | 属性 ID（**C1 白名单**） |
| `--bk_property_name` | 是 | 属性名称 |
| `--bk_property_type` | 是 | 类型：`singlechar`/`longchar`/`int`/`float`/`enum`/`enummulti`/`list`/`bool`/`time`/`date`/`object` 等 |
| `--bk_property_group` | 否 | 可选：引用**已存在**的分组 ID（`bk_group_id`），默认 `default`；**无需用户输入 ID**，留空即可 |
| `--bk_group_name` | 否 | 分组显示名（`bk_group_name`，支持中文/英文）；给定且分组不存在时**自动建组**，系统随机生成 `bk_group_id`，同名复用同一组 |
| `--option` | 否 | 枚举/列表类型的选项 JSON；可为字符串数组 `["online","offline"]` 或完整结构 |
| `--on-duplicate` | 否 | 默认 `error` |

示例（枚举属性）：
```bash
cmdb attribute create --bk_obj_id bk_app_system --bk_property_id status --bk_property_name 状态 \
    --bk_property_type enum --option '["online","offline"]'
# 预期：退出 0；实例表新增 status 列
```

#### `attribute import` — 批量导入属性（CSV）
表头首单元格须为 `bk_property_id`（前面可带“英文名/中文名/类型”说明行，自动跳过）。必填列：`bk_property_id`、`bk_property_name`、`bk_property_type`。
```
cmdb attribute import --csv <文件> --bk_obj_id <模型id> \
    [--group-auto-create] [--atomic|--no-atomic] [--strict] [--verbose] [--on-duplicate overwrite]
```
> **分组列（对齐上游 bk-cmdb）**：scaffold 生成的 `attributes_*.csv` 现为 **13 列**，分组仅用**单列 `bk_property_group_name`**（中文表头"字段分组"，即分组显示名），不再有独立的 `bk_property_group`（分组 ID）列和"分组显示名"/`bk_group_name` 列。`attribute import` 仍**向后兼容**遗留的 14 列格式（含 `bk_property_group` ID 列 + `bk_group_name` 显示名列）。**分组 ID 由系统自动生成，用户只需提供 `bk_property_group_name`（显示名），无需也不应输入 ID、无需新增列。**
> `--group-auto-create`：分组**按显示名优先**解析——同显示名在批次内去重复用同一组；不存在时生成**随机 `bk_group_id`**（`generate_group_id()`）并以该显示名命名。仅遗留的 `bk_property_group` ID 列显式给出且该 ID 必须新建时才校验 C1 白名单；自动建组的随机 ID 不受 C1 约束。
> `description` 列 lite 未实现，会被丢弃并告警（不影响落库）。

示例 CSV（scaffold 生成的 13 列模板，仅 `bk_property_group_name` 单分组列；归默认组）：
```csv
bk_property_id,bk_property_name,bk_property_type,bk_property_group_name,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
ip_addr,管理IP,singlechar,default,,,,管理地址,true,false,false,false,10
```

遗留双列分组 + 显示名去重示例（`bk_property_group` + `bk_group_name`；仍可被 `attribute import` 消费，三条属性共享同一随机分组 ID）：
```csv
bk_property_id,bk_property_name,bk_property_type,bk_property_group,bk_group_name,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
ip,IP,singlechar,network,网络配置,,,,,,true,false,false,false,10
port,端口,int,network,网络配置,,,,,,false,false,false,false,11
remark,备注,longchar,,网络配置,,,,,,false,false,false,false,12
```
```bash
cmdb attribute import --csv /tmp/attr.csv --bk_obj_id bk_app_system
# 预期：退出 0（无失败行），输出 “属性导入 bk_app_system：新增 3 …”
# --group-auto-create 时：仅建一个随机 bk_group_id，三条属性共享（按显示名「网络配置」去重）；remark 未填 ID 也按显示名归同组

cmdb attribute import --csv /tmp/grp_demo.csv --bk_obj_id bk_app_system --group-auto-create
# 预期：退出 0；「网络配置」分组在不存在时被自动建出（随机 bk_group_id + 该中文显示名），三条属性挂到该分组下
```

#### 删除属性（手动）

> 当前 CLI **没有 `attribute delete` 子命令**（属性仅支持 `create` / `import`）。如需移除单个属性，需直接操作 SQLite；若整个模型可丢弃，直接用 `model delete --bk_obj_id <id> --yes` 更省事（但会连模型元数据、实例分表、全部属性与实例一并删除）。
>
> 手动删除单个属性的步骤（操作前务必**备份数据库**，并**停止后端**避免 `database is locked` 退出码 5；或在独立拷贝库上操作）：

1. **定位属性**：查出目标属性的 `id` 与所属模型实例表名。
   ```sql
   SELECT id, bk_property_id, bk_property_name
   FROM cc_ObjAttDes
   WHERE bk_obj_id='<模型id>' AND bk_property_id='<属性id>';
   ```
2. **检查唯一约束引用**：若属性参与 `cc_ObjectUnique`，删除属性前须先清理约束，否则该模型实例后续无法批量更新（唯一键指向不存在属性会报错）。
   ```sql
   SELECT _id, keys FROM cc_ObjectUnique WHERE bk_obj_id='<模型id>';
   -- 解析 keys JSON，若含上一步的 id，则删除/重建该行约束
   ```
3. **删除属性定义**：
   ```sql
   DELETE FROM cc_ObjAttDes
   WHERE bk_obj_id='<模型id>' AND bk_property_id='<属性id>';
   ```
4. **删除实例表列**（本环境 SQLite 3.45 支持 `DROP COLUMN`）：
   ```sql
   ALTER TABLE cc_ObjectBase_0_pub_<模型id> DROP COLUMN <属性id>;
   ```
   > 低版本 SQLite（< 3.35）不支持 `DROP COLUMN`：可忽略该孤儿列（不影响读取），或新建临时表迁移后改名。
5. **校验**：`cmdb model show --bk_obj_id <模型id>` 确认属性已从列表消失。

> 注意：
> - **系统属性不可删**：`id` / `bk_inst_id` / `bk_inst_name` / `bk_obj_id` 由 `model create` 自动维护，删除会导致模型不可用。
> - 列删除后，该属性的历史实例数据**不可恢复**。
> - 若属性曾用于关联（`cc_InstAsst`）或唯一约束，需一并清理对应引用，避免脏数据或更新异常。

### 2.4 instance（实例导入）

```
cmdb instance import --csv <文件> --bk_obj_id <模型id> \
    [--mode auto|insert|upsert] [--upsert-key <列,...>] [--atomic|--no-atomic] \
    [--generate-inst-id|--no-generate-inst-id] [--enum-by-name] [--multivalue-sep ,] \
    [--skip-unknown-columns] [--batch-size 500] [--strict] [--verbose] [--reject-out <路径>]
```
| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--mode` | 否 | `auto` | `auto`：解析 `cc_ObjectUnique` 得匹配键，有则 upsert 无则 insert；`insert`：纯插入；`upsert`：必须有唯一约束 |
| `--upsert-key` | 否 | — | 显式指定匹配列（覆盖 `cc_ObjectUnique` 解析），逗号分隔，每列须过 C1 白名单 |
| `--generate-inst-id` | 否 | `true` | 未给 `bk_inst_id` 时自动生成 |
| `--enum-by-name` | 否 | off | 枚举按名称反查 id（默认按 id 存储） |
| `--multivalue-sep` | 否 | `,` | 多值单元格分隔符 |
| `--skip-unknown-columns` | 否 | off | 表头含不在允许写入列集的列时跳过而非报错 |
| `--reject-out` | 否 | 旁挂文件 | 拒绝汇输出路径，默认 `<CSV目录>/<CSV名>.rejects.csv` |

表头：首行列名 = `bk_inst_name`（**必填**）+ 各属性 ID。`bk_inst_id` 可选（提供则用给定值）。
> **行级拒绝**：坏枚举值、缺 `bk_inst_name`、类型转换失败等，单行计入 `失败` 并写入拒绝汇，不拖垮整批；整体对账通过时退出 0。
> **预检**：`match_cols`（来自 `cc_ObjectUnique` 或 `--upsert-key`）必须全部在表头内，否则退 2。

示例：
```bash
cat > /tmp/inst.csv <<'EOF'
bk_inst_name,status
实例A,online
实例B,offline
EOF
cmdb instance import --csv /tmp/inst.csv --bk_obj_id bk_app_system --mode auto
# 首次：新增 2；再次执行：upsert，仍为 2（无重复）。退出 0
# 拒绝汇（如有坏行）写在 /tmp/inst.csv.rejects.csv
```

### 2.5 table（实例表补建）

```
cmdb table create --bk_obj_id <模型id> [--skip-if-exists|--no-skip-if-exists] [--dry-run]
```
为已存在模型补建实例分表 + 关联分表（若 `model create` 时 `--no-with-tables` 跳过）。
> `--skip-if-exists` 默认开：表已存在则跳过（退出 0）。模型不存在 → 退 3。

### 2.6 scaffold（规格驱动：seed / spec / apply）

#### `scaffold seed` — 生成示例种子目录
```
cmdb scaffold seed [--out-dir ./seed]
```
在 `<out-dir>/<时间戳>/` 下生成 `classifications.csv`、`models.csv`、`attributes_<oid>.csv`、`instances_<oid>.csv`，可作为二次编辑模板。

#### `scaffold spec` — 按 JSON 规格一键建模型+属性
```
cmdb scaffold spec --file <spec.json> [--on-duplicate skip]
```
spec 结构：
```json
{
  "classification": {"bk_classification_id":"bk_spec_cls","bk_classification_name":"规格分类","classification_index":20},
  "model": {"bk_obj_id":"bk_spec_obj","bk_obj_name":"规格模型","bk_classification_id":"bk_spec_cls"},
  "groups": [{"bk_group_id":"default","bk_group_name":"默认","bk_group_index":0}],
  "attributes": [{"bk_property_id":"alias","bk_property_name":"别名","bk_property_type":"singlechar"}]
}
```
> **预检（退 2）**：`model` 须为含 `bk_obj_id` 的对象；若提供 `classification` 须含 `bk_classification_id`。缺则退出 2（不落库）。

#### `scaffold apply` — 按 seed 目录端到端落地
```
cmdb scaffold apply --dir <seed目录> [--on-duplicate overwrite] [--with-system-props] \
    [--with-tables] [--atomic|--no-atomic] [--group-auto-create] [--strict] [--verbose] \
    [--manifest-out <路径>]
```
严格按阶段序执行：分类 → 模型 → 属性 → 实例。运行清单写 `<dir>/.run.json`（sha256 / 行数 / 参数 / 各阶段结果 / 对账标志）。

示例：
```bash
cmdb scaffold seed --out-dir /tmp/seed_out
cmdb scaffold apply --dir /tmp/seed_out/$(ls -1t /tmp/seed_out | head -1)
# 预期：退出 0；分类/模型/属性/实例依次落地；输出对账 ✓；生成 .run.json
```

#### `scaffold from-csv` — 从实例 CSV 反推 seed 目录

把一份「首行英文表头 + 实例数据」的单模型 CSV，反向推导为与 `scaffold seed` 同构的目录（可被 `apply` 直接消费）。**全部规则通过才生成，否则中断零落盘**（详见设计文档 §5.6.3）。

```
cmdb scaffold from-csv --csv <实例数据.csv> [--out-dir ./seed] \
    [--classification-id bk_import] [--classification-name 分类名] \
    [--model-name 模型名] [--dry-run] [--json]
```

5 条硬规则（+ 2.1 保留列处理）：
1. 文件名 stem → 模型 `bk_obj_id`，必须英文且匹配 `^[a-z][a-z0-9_]*$`；
2. 表头每个英文 key → 属性 `bk_property_id`，逐一匹配同一正则；
2.1 **系统/保留列处理**：`bk_inst_name` 是实例名，**允许原样保留**；其余系统保留列（`id`/`_id`/`bk_inst_id`/`bk_obj_id`/`bk_supplier_account`/`create_time`/`last_time`/`bk_operate_time`）**不拒绝**，自动对属性 id 与实例列加前缀 `u_` 区分（如 `bk_obj_id`→`u_bk_obj_id`），避免覆盖系统列；`bk_inst_name` 缺列则自动补为必填 `singlechar`；
3. 每个属性类型默认 `singlechar`（不解析数据推断）；**中文属性名 (`bk_property_name`) 默认用同一英文 key 原值补填**；
4. 规则 1/2 任一不通过 → 输出**问题记录报告**、退出码 2、不生成任何文件；
5. 通过 → 输出 `seed/<12位时间戳>/` 目录（`classifications.csv` / `models.csv` / `attributes_<oid>.csv` / `instances_<oid>.csv`）。

示例：
```bash
# 输入 servers.csv（首行英文表头，其余为数据行）
cmdb scaffold from-csv --csv servers.csv --classification-id bk_application
# 预期：退出 0；生成 ./seed/260805002341/{classifications,models,attributes_servers,instances_servers}.csv
# 全部属性 singlechar；用户可编辑（如把 region 改 enum 并补 option）后再 apply

# 校验失败示例（文件名大写 + 表头含中文/数字开头）
cmdb scaffold from-csv --csv Servers.csv
# 预期：退出 2；打印问题记录（规则1：stem 'Servers'；规则2：'IP 地址'/'1st_field'），不生成文件
```

> 标识符同源：`bk_obj_id` 与 `bk_property_id` 共用白名单 `IDENTIFIER_RE = ^[a-z][a-z0-9_]*$`（`app/cli/safety.py`），校验严格匹配、不做隐式转换。`attributes_<oid>.csv` 采用 13 列 seed 模板（仅 `bk_property_group_name` 单分组列，对应中文表头"字段分组"，已弃用独立的 `bk_property_group` / `bk_group_name` 列，非 17 列 export 模板），与 `apply` 兼容。

#### 自定义属性分组（bk_property_group / bk_group_name）

seed 生成的目录里**没有** `property_group*.csv`——这是有意为之：`bk_property_group` 不在「分类 → 模型 → 属性 → 实例」的四级导入链中。其创建规则为：

- **`default` 分组由 `model create` / `create_model_core` 自动建出**。seed 模板中所有属性的 `bk_property_group_name` 列都填 `default`，因此无需单独的「分组文件」。
- 分组是**按属性逐行引用**的：scaffold 生成的 `attributes_*.csv` 仅含单列 `bk_property_group_name`（中文表头"字段分组"），填分组 **显示名**（推荐，唯一用户态输入）；遗留 CSV 也可用 `bk_group_name`（显示名）+ `bk_property_group`（ID，可选）双列。**分组 ID 由系统自动生成，用户无需输入 ID、无需新增列。**

**两列语义（对齐上游 bk-cmdb）**：

| 列 | 含义 | 说明 |
| --- | --- | --- |
| `bk_property_group_name` | 分组 **显示名**（scaffold 生成模板用的单分组列，对应中文表头"字段分组"） | 推荐列；scaffold 生成的 `attributes_*.csv` 仅含此列，用户填分组显示名（如 `网络配置`）即可，ID 由系统生成 |
| `bk_group_name` | 分组 **显示名**（`bk_group_name`，遗留兼容列） | 用户可读名称（支持中文/英文）；建组与归属的用户态输入之一 |
| `bk_property_group` | 分组 **ID**（`bk_group_id`，遗留兼容列） | 语义标识；可空，缺省由系统随机生成（`default` 分组除外） |

`--group-auto-create` 时的分组解析（详见 CLI 设计文档 §5.11.9，已改为**显示名优先**）：先按 `bk_group_name` 显示名精确匹配/去重复用 → 再按 `bk_property_group` ID 兼容旧 CSV → 都不命中才自动建组。自动建组生成**随机 `bk_group_id`**（`generate_group_id()`，20 位 base32 小写串，对齐上游 `xid.New()`），并以 `bk_group_name` 作为显示名；**同一显示名在导入批次内去重，复用同一 ID**（镜像上游 `grpNameIDMap`），因此多条属性填同一显示名只会建出一个分组。

**要新增一个自定义分组（如「网络配置」），最简做法：**

1. 在 `attributes_<oid>.csv` 中，把目标属性行的 `bk_property_group_name` 列填为 `网络配置`（scaffold 模板仅此单列，无需再填 `bk_property_group`）；
2. 跑 `scaffold apply` 并加 `--group-auto-create`：

```bash
cmdb scaffold apply --dir <csv目录> --group-auto-create
# 预期：退出 0；「网络配置」分组在不存在时被自动建出（随机 bk_group_id + 该中文显示名），对应属性挂到该分组下
```

> 注意：
> - **CLI 没有独立 `group create` 子命令**。分组创建由属性导入（`attribute import` 的 `--group-auto-create`）或 `attribute create` 的 `--bk_group_name`（给定且不存在即自动建组）隐式完成。
> - **显式创建 / 改名 / 删除分组**请走后端分组 API：`POST` / `PUT` / `DELETE /api/v1/models/<id>/property-groups`（默认分组不可删除，删组后其下属性回落 `default`）。
> - C1 适用范围收窄：自动建组的随机 `bk_group_id` **不来自用户输入、不受 C1 白名单约束**；仅当用户显式给出 `bk_property_group` ID 且该 ID 必须新建时才校验 C1。内置 ID（`default`/`auto`/`role`/`proc_port`）的显示名由 `KNOWN_GROUP_NAMES` 单一真相源兜底。
> - 向后兼容：旧 CSV 仅含 `bk_property_group` ID 列仍可导入；未命中且开了 `--group-auto-create` 时按该 ID 建组（须过 C1），显示名取 `KNOWN_GROUP_NAMES` 兜底（未命中则用裸 ID 当显示名）。
> - 若不加 `--group-auto-create` 且 `bk_property_group` 指向不存在的分组，该属性行会被**行级拒绝**（计入失败、不回滚整批）。

---

## 3. CSV 文件格式汇总

| 导入 | 表头（必填加粗） | 说明 |
| --- | --- | --- |
| classification | **bk_classification_id**, **bk_classification_name**, bk_classification_icon, ispre, classification_index | 支持中文别名；`classification_index` 控制分类显示顺序（升序） |
| model | **bk_obj_id**, **bk_obj_name**, **bk_classification_id**, bk_obj_icon, ispre, bk_ishidden, bk_ispaused, obj_sort_number | |
| attribute | 首单元格=`bk_property_id`；**bk_property_id**, **bk_property_name**, **bk_property_type**, **bk_property_group_name**(分组显示名，scaffold 生成模板用此单列), bk_property_group(分组ID,可选/遗留兼容列), bk_group_name(显示名,遗留兼容列), option, …（scaffold 生成 13 列；遗留双列 14 列兼容） | 可带"英文名/类型"说明行；分组列**推荐用 `bk_property_group_name`**（显示名），`bk_property_group` / `bk_group_name` 为遗留兼容列 |
| instance | **bk_inst_name** + 属性 ID | `bk_inst_id` 可选 |

> 所有 CSV 默认以 `utf-8-sig` 读取（自动剔除 BOM），分隔符默认 `,`。
> 枚举/列表 `option` 写 JSON：简单数组 `["online","offline"]` 会被规范为完整结构。

---

## 4. 典型工作流（步骤）

### 4.1 逐命令新建并录入（推荐先建沙箱库）
```bash
# 0) 准备沙箱库
cp cmdb_dev.db /tmp/cli_test.db
DB=/tmp/cli_test.db

# 1) 分类
cmdb classification create --bk_classification_id bk_application --bk_classification_name 应用系统 --db $DB
# 2) 模型（含系统属性 + 分表 + 默认唯一约束）
cmdb model create --bk_obj_id bk_app_system --bk_obj_name 应用系统 --bk_classification_id bk_application --db $DB
# 3) 属性（枚举 + 单字符）
cmdb attribute create --bk_obj_id bk_app_system --bk_property_id name  --bk_property_name 名称 --bk_property_type singlechar --isrequired true --db $DB
cmdb attribute create --bk_obj_id bk_app_system --bk_property_id status --bk_property_name 状态 --bk_property_type enum --option '["online","offline"]' --db $DB
# 4) 录入实例（auto→upsert by bk_inst_name）
printf 'bk_inst_name,status\n实例A,online\n实例B,offline\n' > /tmp/inst.csv
cmdb instance import --csv /tmp/inst.csv --bk_obj_id bk_app_system --mode auto --db $DB
# 5) 校验
cmdb model show --bk_obj_id bk_app_system --db $DB
```

### 4.2 scaffold 一键生成（演示 / CI）
```bash
cmdb scaffold seed --out-dir /tmp/seed_out                                   # 生成模板
cmdb scaffold apply --dir /tmp/seed_out/$(ls -1t /tmp/seed_out | head -1) --db /tmp/cli_test.db
# 等价于 4.1 的“分类+模型+属性+实例”全流程，并产出 .run.json 作为运行凭证
```

### 4.3 安全预演
任意写命令加 `--dry-run` 仅打印计划、不落库（如 `model create ... --dry-run`、`scaffold apply ... --dry-run`、`instance import ... --dry-run`）。

---

## 5. 测试参考（checklist）

> 执行前准备沙箱库：`cp cmdb_dev.db /tmp/cli_test.db && DB=/tmp/cli_test.db`。
> 下面“预期退出码”是断言点；现象用于人工/脚本核对。

### 5.1 正向（应全部退出 0）

| # | 场景 | 命令（省略 `--db $DB`） | 预期退出码 | 预期现象 |
| --- | --- | --- | --- | --- |
| P1 | 建分类 | `classification create --bk_classification_id bk_application --bk_classification_name 应用系统` | 0 | 输出 `分类 ...: create` |
| P1a | 分类排序 | `classification create --bk_classification_id bk_top --bk_classification_name 置顶 --classification_index -5` 后查 `classifications/find/classificationobject` | 0 | `bk_top` 排在最前（`ORDER BY classification_index, id` 生效） |
| P2 | 建模型 | `model create --bk_obj_id bk_app_system --bk_obj_name 应用系统 --bk_classification_id bk_application` | 0 | 自动建两张分表 + cc_ObjectUnique |
| P3 | 建属性 | `attribute create --bk_obj_id bk_app_system --bk_property_id status --bk_property_type enum --option '["online","offline"]'` | 0 | 实例表新增 status 列 |
| P4 | 实例首导 | `instance import --csv /tmp/inst.csv --bk_obj_id bk_app_system --mode auto` | 0 | 新增 N 行 |
| P5 | 实例重导（upsert） | 同 P4 再跑一次 | 0 | 行数不变（覆盖，无重复） |
| P6 | 模型查询 | `model show --bk_obj_id bk_app_system` / `model list` | 0 | 正常列出 |
| P7 | 补表 | `table create --bk_obj_id bk_app_system` | 0 | 已存在则“跳过” |
| P8 | scaffold seed→apply | `scaffold seed --out-dir /tmp/seed_out` → `scaffold apply --dir <最新>` | 0 | 全阶段落地，对账 ✓，生成 .run.json |
| P9 | dry-run | 任意写命令加 `--dry-run` | 0 | 仅打印，库未变 |

### 5.2 边界 / 异常（断言退出码）

| # | 场景 | 命令 | 预期退出码 | 预期现象 |
| --- | --- | --- | --- | --- |
| E1 | 非法模型 ID | `model create --bk_obj_id Bad-Id --bk_obj_name 坏 --bk_classification_id bk_application` | 2 | “非法标识符” |
| E2 | 依赖缺失（属性建到不存在模型） | `attribute create --bk_obj_id no_such --bk_property_id x --bk_property_name X --bk_property_type singlechar` | 3 | “模型不存在” |
| E3 | 依赖缺失（模型用不存在分类） | `model create --bk_obj_id x --bk_obj_name X --bk_classification_id no_cls` | 3 | “分类不存在” |
| E4 | 已存在 + error | 连续两次 `classification create --bk_classification_id bk_dup --bk_classification_name 重复` | 0 → 4 | 第二次退 4 “分类已存在” |
| E5 | 删模型未确认 | `model delete --bk_obj_id bk_app_system` | 2 | “请加 --yes 确认” |
| E6 | 实例表头缺 bk_inst_name | 用仅含 `status` 列的 CSV 导入 | 2 | “表头缺少必填列 bk_inst_name” |
| E7 | match_cols 不在表头 | 手工把唯一约束指向不在表头的属性后导入 | 2 | “匹配键列不在 CSV 表头中” |
| E8 | spec 缺 model | `scaffold spec --file` 指向 `{"classification":{...}}` | 2 | “spec 缺少必填字段 model.bk_obj_id” |
| E9 | spec classification 缺 id | spec 含 `classification` 但无 `bk_classification_id` | 2 | “spec.classification 缺少 bk_classification_id” |
| E10 | DB 被锁定 | 后端占用连接时执行写命令 | 5 | “database is locked” |

### 5.3 行级鲁棒性（单坏行不回滚整批）

| # | 场景 | 命令 | 预期退出码 | 预期现象 |
| --- | --- | --- | --- | --- |
| R1 | 分类 CSV 含 1 行坏 bool（ispre=maybe） | `classification import --csv <含坏行>` | 1（部分失败信号） | 好行全部落库（新增 2），坏行计失败 1 |
| R2 | 模型 CSV 含 1 行坏数值（obj_sort_number=abc） | `model import --csv <含坏行>` | 1 | 好模型落库，坏行失败 1 |
| R3 | 属性 CSV 含 1 行坏 bool | `attribute import --csv <含坏行> --bk_obj_id <已建模型>` | 1 | 好属性落库，坏行失败 1 |
| R4 | 实例 CSV 含 1 行坏枚举 | `instance import --csv <含坏行>` | 0（对账通过） | 好行落库，坏行失败 1，拒绝汇写 `<csv>.rejects.csv` |
| R5 | 上述任一加 `--strict` | 同 R1–R3 加 `--strict` | 1 | 整批中断、回滚（好行也不落库） |

> R1–R3 退出 1 属**设计行为**（部分失败需以非零码上报）；实例导入（R4）因对账仍通过而返回 0。核心断言是：**单坏行不会导致前面已写入行丢失**（对比整改前“裸异常穿透循环 → 整批回滚”）。

---

## 6. 排错速查

| 现象 | 原因 / 处理 |
| --- | --- |
| `退出 5 database is locked` | 后端进程占用同一 SQLite 连接；停止后端或换独立沙箱库后重试。 |
| `退出 2 非法标识符` | `bk_obj_id` / `bk_property_id` / 分组 ID / `--upsert-key` 须匹配 `^[a-z][a-z0-9_]*$`；分类 ID 不受此限。 |
| `退出 2 表头缺少必填列` | 实例表头必须有 `bk_inst_name`；分类/模型/属性 CSV 必填列见 §3。 |
| `退出 2 匹配键列不在 CSV 表头中` | 模型被手工设了非 `bk_inst_name` 唯一键，而导入 CSV 不含该列；补列或改唯一约束。 |
| `退出 3 模型/分类不存在` | 先建依赖（分类 → 模型 → 属性/实例）。 |
| `退出 4 已存在` | 重复创建且 `--on-duplicate error`（默认）；改用 `skip` / `overwrite`。 |
| 实例导入 0 行但退出 0 | 可能表头含未知列被拦截（`--skip-unknown-columns` 跳过）或 CSV 无数据行（skip_empty 跳过）。 |
| `<csv>.rejects.csv` 出现 | 存在行级拒绝；按列定位坏值修复后重导。 |

---

## 7. 版本与范围

- 本手册对应 `app/cli` 实现（含审查整改：行级异常全捕获、match_cols 预检、spec schema 校验）。
- 不替代 `migrate.py` 全量初始化；首次建库仍走迁移脚本。
- 仅支持 SQLite（lite 固定供应商账号 `0`）。
