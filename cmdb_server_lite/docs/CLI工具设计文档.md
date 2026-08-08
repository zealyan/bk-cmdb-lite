# CMDB-Lite CLI 工具设计文档

> 设计目标：提供一套命令行工具，在 **cmdb_server_lite** 项目中以最小心智负担完成 **新建模型、新建属性、新建实例表** 三类操作，直接对数据库执行与 `新增模型数据库操作指南.md` 一致的写操作，避免每次手动改 `migrate.py` 后全量重建。

---

## 1. 目标与范围

| 维度   | 说明                                                                                   |
| ---- | ------------------------------------------------------------------------------------ |
| 直接目标 | `cmdb` 命令行支持三类写操作：**模型（model）**、**属性（attribute）**、**实例表（table）**                     |
| 间接支撑 | 创建模型时一并完成 **分类校验、默认分组、4 个系统属性、实例分表、实例关联分表**，达到"一次命令即可在前端看到并录入实例"的状态                  |
| 非目标  | 不替代 `migrate.py` 的全量初始化（首次建库仍走迁移脚本）；不实现实例数据批量导入（指南 3.5 的 `instances/*.json` 由迁移脚本负责） |
| 使用场景 | 开发期快速加字段/加模型、演示环境临时扩展、CI 中按规格生成模型                                                    |

**核心约束（来自指南）**：

- 实例表命名 `cc_ObjectBase_0_pub_{bk_obj_id}`，关联表命名 `cc_InstAsst_0_pub_{bk_obj_id}`，其中 `0` 为固定供应商账号。
- 每个模型只需 **Default 分组**（`default` 分组 ID），**不再强制创建 base 分组**（修正旧规则"至少 default + base"）。
- 每个模型必须预置 **4 个系统属性**（`id` / `bk_inst_id` / `bk_inst_name` / `bk_obj_id`）。
- 实例统一以 `bk_inst_id` 作为前后端标识，`id` 仅作数据库主键。
- **标识符安全（防注入，C1）**：所有拼接待 DDL 的标识符（`bk_obj_id` / `bk_property_id` / 分组 ID / CSV 表头列名）必须经过白名单校验 `^[a-z][a-z0-9_]*$`，不通过直接拒绝退出；标识符统一转义内部 `"` 后以双引号包裹拼入 SQL。**命名参数（`:key`）仅保护 VALUE，绝不保护标识符**——禁止把用户输入直接插值进表名/列名。
- **唯一约束默认写入（C3）**：每个经 CLI 创建的模型，默认（可由 `--unique-by` 覆盖）向 `cc_ObjectUnique` 写入一条以 `bk_inst_name` 为键的唯一约束（结构见 §5.2 步骤 8），保证 `instance import` 具备 UPSERT 能力，避免"无唯一组合则恒为 INSERT"导致的重复实例。

---

## 2. 技术选型与运行方式

| 项      | 选择                                                       | 理由                                                   |
| ------ | -------------------------------------------------------- | ---------------------------------------------------- |
| 语言     | Python 3.11                                              | 与后端一致，可直接 `import` 项目模块                              |
| 参数解析   | `argparse` 子命令（或 `click`/`typer`）                        | 子命令天然对应 model/attribute/table 三类操作                   |
| 数据库访问  | **复用** `app.db.executor.{query_one, query_all, execute}` | 与后端共用连接池与方言兼容，避免重复实现                                 |
| 类型映射   | **复用** `app.definitions.get_sql_type()`                  | 保证属性类型→SQL 类型与迁移脚本 100% 一致（单一真相源）                    |
| ID 生成  | **复用** `app.utils.tools.generate_id()`                   | 系统属性 / 分组记录主键（`id` 列）/ 关联记录的主键生成规则统一                 |
| 分组 ID 生成 | **复用** `app.utils.tools.generate_group_id()`        | 分组语义标识 `bk_group_id` 的随机全局唯一串（对齐上游 `xid.New()`）；详见 §5.11.9 |
| 系统属性模板 | **复用** `app.migrate.migrate.SYSTEM_PROPERTIES`           | 4 个系统属性的标志位（bk_isapi/bk_issystem/ispre/editable）直接复用 |

**入口建议**（文档示意，非实现）：

```bash
# 方式一：模块方式（推荐，自动继承项目路径与 .env）
python3 -m app.cli.cmdb <subcommand> [options]

# 方式二：可执行脚本（需在脚本内手动加载 settings / engine）
python3 cmdb_cli.py <subcommand> [options]
```

**运行约束（重要，C4）**：lite 以 supervisord 拉起 Flask 常驻，`cmdb_dev.db` 被后端连接占用。CLI 直接写同一 SQLite 文件时，若后端持连可能触发 `database is locked`。建议：

- **导入前停止后端**：`supervisorctl stop cmdb`（或停掉占用连接的进程），导入完成后再 `supervisorctl start cmdb`；开发自测环境推荐此方式。
- **或改用 WAL 模式**：初始化时执行 `PRAGMA journal_mode=WAL`，读写互不阻塞（需后端与 CLI 共用同一 WAL 设置）。
- **或复用后端连接**：CLI 通过项目 `engine` 获取连接，与后端共用连接池，而非另开独立连接。

> 约定：CLI 运行前置条件为"目标 SQLite 文件当前无长期写锁"；若检测到 `database is locked`，应先释放后端连接再重试。



---

## 3. 命令总览

| 命令                           | 作用                               | 写入的表                                                                                                |
| ---------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------- |
| `cmdb classification create` | 新建模型分类                           | `cc_ObjClassification`                                                                              |
| `cmdb model create`          | 新建模型（含分组、系统属性、实例表、关联表）           | `cc_ObjDes` / `cc_PropertyGroup` / `cc_ObjAttDes` / `cc_ObjectBase_0_pub_*` / `cc_InstAsst_0_pub_*` |
| `cmdb attribute create`      | 为已有模型新增属性，并同步 ALTER 实例表          | `cc_ObjAttDes` + `ALTER cc_ObjectBase_0_pub_*`                                                      |
| `cmdb attribute import`      | 从 CSV 模板批量导入/更新属性（解析分组、ALTER 实例表、事务开关） | `cc_ObjAttDes` + `cc_PropertyGroup` + `ALTER cc_ObjectBase_0_pub_*`                                |
| `cmdb classification import` | 从 CSV 批量导入模型分类（覆盖/跳过、事务开关）             | `cc_ObjClassification`                                                                          |
| `cmdb model import`         | 从 CSV 批量导入模型（可选连带分组/系统属性/实例表/关联表、事务开关） | `cc_ObjDes` / `cc_PropertyGroup` / `cc_ObjAttDes` / `cc_ObjectBase_0_pub_*` / `cc_InstAsst_0_pub_*` |
| `cmdb instance import`       | 从 CSV 批量导入**实例**到 `cc_ObjectBase_0_pub_*`（表头预检；无唯一组合则 INSERT、有则 UPSERT；事务开关） | `cc_ObjectBase_0_pub_*` + `cc_ObjectUnique`（判定 upsert 键） |
| `cmdb table create`          | 仅为已有模型（元数据已存在）补建实例表与关联表          | `cc_ObjectBase_0_pub_*` / `cc_InstAsst_0_pub_*`                                                     |
| `cmdb model show`            | 查看模型元信息、分组、属性列表（只读校验）            | 查询 `cc_ObjDes` / `cc_PropertyGroup` / `cc_ObjAttDes`                                                |
| `cmdb model delete`          | 删除模型（元数据 + 实例表 + 关联表，反向清理）       | 以上各表                                                                                                |
| `cmdb scaffold`              | 从 JSON/YAML 规格一次性创建 分类+模型+属性（高级）；另支持 CSV 模式 seed/apply（§5.6.1/§5.6.2） | 组合上述全部                                                                                              |
| `cmdb scaffold seed`        | 生成带示例的 CSV 模板目录（12 位时间戳目录名，参考 bk_switch + bk_deployment） | 仅生成文件（不落库） |
| `cmdb scaffold apply`       | 读取 seed 目录内全部 CSV，按依赖顺序批量执行（分类→模型→属性→实例） | 组合 §5.9/§5.10/§5.7/§5.8 各表 |

---

## 4. 全局选项与约定

| 选项             | 默认                        | 说明                             |
| -------------- | ------------------------- | ------------------------------ |
| `--db PATH`    | 取 `settings.DATABASE_URI` | 显式指定 SQLite 文件路径；不传则走项目配置      |
| `--env NAME`   | `development`             | 与项目 `config_by_env` 联动，决定连接哪个库 |
| `--dry-run`    | 关闭                        | 仅打印将要执行的 SQL，不落库（强烈建议用于复核）     |
| `--yes` / `-y` | 关闭                        | 跳过危险操作（建表/删表）的二次确认             |
| `--json`       | 关闭                        | 结果以 JSON 输出，便于管道编排             |
| `--on-duplicate` | 见各命令 | 冲突处理统一策略：`error`（已存在则报错退出）/ `skip`（跳过已存在）/ `overwrite`（覆盖已存在）；**默认因命令而异**（create 类默认 `error`、import 类默认 `overwrite`），取代原 `--force` |
| `--reject-out` | 否 | 拒绝汇输出路径（坏行持久化，见 §5.11.6）；默认 `<dir>/<file>.rejects.csv`（无目录取 `./<file>.rejects.csv`） |
| `--manifest-out` | 否 | 运行清单输出路径（校验和 + 行数 + 参数，见 §5.11.13）；默认 `./.run.json`（在 `seed/<ts>` 内取 `<dir>/.run.json`） |

**通用校验约定**：

- 写操作前先 `query_one` 校验目标记录是否已存在，按 `--on-duplicate` 决定：`error` 报错退出（退出码 4）、`skip` 跳过、`overwrite` 覆盖。
- 所有写入统一经过 `execute()` 的命名参数（`:key`）方式，杜绝 VALUE 注入；**表名/列名等标识符不属命名参数保护范围，须先经 §1 白名单校验**（防 DDL 注入，C1）。
- 供应商账号统一写 `'0'`（lite 不支持多租户）。
- 错误输出双轨：退出码为主（`--json` 仅提供结构化明细，不改变退出码）；`--dry-run` 成功返回 `0`，预检失败返回 `2`。

---

## 5. 命令详细设计

### 5.1 `cmdb classification create`

**入参**

| 参数                         | 必填 | 说明                            |
| -------------------------- | -- | ----------------------------- |
| `--bk_classification_id`   | 是  | 分类 ID（唯一，如 `bk_application`）  |
| `--bk_classification_name` | 是  | 分类名称（前端导航显示，如 `应用系统`）         |
| `--bk_classification_icon` | 否  | 图标 class，默认 `icon-cc-default` |
| `--id`                     | 否  | 数字 ID，缺省取 `MAX(id)+1`         |
| `--ispre`                  | 否  | 是否预置，默认 `false`               |
| `--classification_index`   | 否  | 分类**排序序号**（整数，默认 `0`；升序，越小越靠前），写入 `cc_ObjClassification.classification_index`。别名 `--index` 兼容旧写法 |

**数据库操作**（对应指南 2.1）

```sql
INSERT INTO cc_ObjClassification
  (id, bk_classification_id, bk_classification_name, bk_classification_icon, ispre, classification_index, bk_supplier_account)
VALUES
  (:id, :bk_classification_id, :bk_classification_name, :bk_classification_icon, :ispre, :classification_index, '0');
```

> **排序机制**：资源目录页渲染顺序完全由后端 `SELECT ... FROM cc_ObjClassification ORDER BY classification_index, id` 决定（前端 `store/objectModelClassify` 不再对分类做二次排序）。分类间先后 = `classification_index` 升序；同值则按 `id` 稳定排序。缺省 `0` 即维持建表顺序。

**校验**：`bk_classification_id` 已存在则按 `--on-duplicate` 处理（`error` 默认报错退出，`skip` 跳过，`overwrite` 覆盖）。

---

### 5.2 `cmdb model create`

这是最核心的复合命令，一次完成模型元信息 + 分组 + 系统属性 + 实例表 + 关联表（对应指南 1.2 步骤 1/2/3/6 与 2.2/2.3/2.4/2.7/2.8）。

**入参**

| 参数                       | 必填 | 说明                                    |
| ------------------------ | -- | ------------------------------------- |
| `--bk_obj_id`            | 是  | 模型唯一 ID（主键，如 `bk_application_system`） |
| `--bk_obj_name`          | 是  | 模型名称（如 `应用系统`）                        |
| `--bk_classification_id` | 是  | 所属分类 ID（需已存在，否则先报"分类不存在"）             |
| `--bk_obj_icon`          | 否  | 模型图标，默认 `icon-cc-default`             |
| `--ispre`                | 否  | 是否预置，默认 `false`                       |
| `--obj_sort_number`      | 否  | 排序编号，默认 `0`                           |
| `--with-system-props`    | 否  | 是否自动注入 4 个系统属性，默认开启                   |
| `--with-tables`          | 否  | 是否自动建实例表与关联表，默认开启                     |
| `--unique-by`            | 否  | 默认唯一约束的键属性（逗号分隔，如 `bk_inst_name`），默认 `bk_inst_name`；覆盖 §5.2 步骤 8 的默认键 |

**执行步骤（事务内）**

1. **校验分类**：`SELECT 1 FROM cc_ObjClassification WHERE bk_classification_id = :cid`，不存在报错。
2. **校验模型**：`SELECT 1 FROM cc_ObjDes WHERE bk_obj_id = :oid`，已存在则按 `--on-duplicate` 处理（`error` 默认报错退出，`skip` 跳过，`overwrite` 覆盖元数据）。
3. **写入模型**（对应指南 2.2）
   ```sql
   INSERT INTO cc_ObjDes
     (_id, id, bk_obj_id, bk_obj_name, bk_obj_icon, bk_classification_id,
      ispre, bk_ishidden, bk_ispaused, obj_sort_number,
      creator, modifier, bk_supplier_account)
   VALUES
     (:bk_obj_id, :id, :bk_obj_id, :bk_obj_name, :bk_obj_icon, :bk_classification_id,
      :ispre, false, false, :obj_sort_number, 'admin', 'admin', '0');
   ```
   > **ID 生成契约**：本行 `_id` 取模型自身 ID（`_id = bk_obj_id`，每模型仅一行，唯一），`id = generate_id()`（全局唯一递增整数）。**所有 `generate_id()` 调用与后端 API 共用同一序列**，避免前后端撞号。
4. **写入 Default 分组**（按本设计规则，每个模型只需 `default` 一个分组，不再强制 base）
   ```sql
   INSERT INTO cc_PropertyGroup
     (_id, id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index,
      bk_isdefault, is_collapse, ispre, bk_biz_id, creator, modifier, bk_supplier_account)
   VALUES
     (:_id, :id, :bk_obj_id, 'default', '默认', 0, true, false, true, 0, 'admin', 'admin', '0');
   ```
   > 说明：范本 `bk_switch` 在库中同时含 `default` 与 `base` 两个分组，但本设计已修正为"仅需 Default 分组"，故 CLI 只创建 `default`；业务属性默认也归入 `default`。
5. **写入 4 个系统属性**（以实际库 `bk_switch` 模型为范本，标志位保持完全一致；分组统一归入 `default`）
   > 范本来源：查询 `cmdb_dev.db` 中 `bk_switch` 模型的 `cc_ObjAttDes` 记录，其 4 个系统属性的真实标志位如下（与 `app.migrate.migrate.SYSTEM_PROPERTIES` 模板一致）：
   >
   > - `id` / `bk_inst_id` / `bk_inst_name` 的 `bk_issystem` 均为 **false**（旧文档误写为 true）
   > - 仅 `bk_obj_id` 的 `bk_issystem` 为 **true**
   > - `bk_inst_name` 在范本中归属 `base` 分组；按本设计"仅需 Default 分组"的规则，CLI 将其统一归入 `default` 分组
   | bk_property_id | 类型         | bk_property_group | bk_isapi | bk_issystem | ispre | editable | bk_ishidden | isreadonly | bk_property_index |
   | -------------- | ---------- | ----------------- | -------- | ----------- | ----- | -------- | ----------- | ---------- | ----------------- |
   | `id`           | int        | default           | true     | **false**   | true  | false    | false       | true       | -1                |
   | `bk_inst_id`   | int        | default           | true     | **false**   | true  | false    | false       | true       | 0                 |
   | `bk_inst_name` | singlechar | default           | false    | **false**   | true  | true     | false       | false      | 1                 |
   | `bk_obj_id`    | singlechar | default           | true     | **true**    | true  | false    | true        | true       | 2                 |
   > **ID 生成契约（修复确定性 bug，C2）**：下方 4 行 INSERT 的 `_id` 与 `id` 必须由调用方**逐行独立生成**，**禁止复用同一 `:id` 值**（否则 4 行共享同一 `id` → `cc_ObjAttDes.id` 主键冲突，整事务回滚）。约定：`_id = "{bk_obj_id}.{bk_property_id}"`（如 `bk_switch.id`、`bk_switch.bk_inst_name`），`id = generate_id()`（每次调用返回唯一递增整数）。`cc_PropertyGroup._id` 同理为 `"{bk_obj_id}.{bk_group_id}"`（如 `bk_switch.default`）。
   ```sql
   INSERT INTO cc_ObjAttDes
     (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type,
      bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
      bk_isapi, bk_issystem, ispre, bk_property_index, unit, placeholder, editable, option, bk_supplier_account)
   VALUES
     -- id：API 内部主键，前端完全不显示
     (:_id, :id, :bk_obj_id, 'id', '数据ID', 'int', 'default',
      0, 0, 0, 1, 1, 0, 1, -1, '', '', 0, NULL, '0'),
     -- bk_inst_id：实例ID，API 内部字段
     (:_id, :id, :bk_obj_id, 'bk_inst_id', '实例ID', 'int', 'default',
      0, 0, 0, 1, 1, 0, 1, 0, '', '', 0, NULL, '0'),
     -- bk_inst_name：实例名称，前端展示且可编辑
     (:_id, :id, :bk_obj_id, 'bk_inst_name', '实例名称', 'singlechar', 'default',
      1, 0, 0, 0, 0, 0, 1, 1, '', '请输入实例名称，用于标识该实例', 1, NULL, '0'),
     -- bk_obj_id：模型ID，API+隐藏，完全不可见
     (:_id, :id, :bk_obj_id, 'bk_obj_id', '模型ID', 'singlechar', 'default',
      1, 0, 1, 1, 1, 1, 1, 2, '', '', 0, NULL, '0');
   ```
6. **建实例分表**（对应指南 2.7，仅系统列，业务列后续由 `attribute create` ALTER 追加）
   ```sql
   CREATE TABLE IF NOT EXISTS "cc_ObjectBase_0_pub_{bk_obj_id}" (
     _id VARCHAR,
     id INTEGER PRIMARY KEY,
     bk_inst_id INTEGER NOT NULL,
     bk_inst_name VARCHAR NOT NULL,
     bk_supplier_account VARCHAR DEFAULT '0',
     bk_obj_id VARCHAR NOT NULL,
     create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     bk_operate_time TIMESTAMP
   );
   ```
7. **建实例关联分表**（对应指南 2.8）
   ```sql
   CREATE TABLE IF NOT EXISTS "cc_InstAsst_0_pub_{bk_obj_id}" (
     _id VARCHAR,
     id INTEGER PRIMARY KEY,
     bk_obj_id VARCHAR NOT NULL,
     bk_inst_id INTEGER NOT NULL,
     bk_asst_obj_id VARCHAR NOT NULL,
     bk_asst_inst_id INTEGER NOT NULL,
     bk_obj_asst_id VARCHAR NOT NULL,
     bk_relation_type_id VARCHAR NOT NULL,
     bk_supplier_account VARCHAR DEFAULT '0'
   );
   ```
   > **标识符安全（C1）**：上述表名中的 `{bk_obj_id}` 来自用户输入，拼入 DDL 前**必须**经 §1 白名单 `^[a-z][a-z0-9_]*$` 校验并转义；校验失败直接拒绝，绝不把原始输入拼进 `CREATE TABLE` / `ALTER TABLE`。
8. **写入默认唯一约束**（对应指南八，保证实例可 UPSERT，C3）
   键属性 = `--unique-by` 值（默认 `bk_inst_name`）。先取该属性的 `id`：`SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:oid AND bk_property_id=:key_prop`（记为 `key_attr_id`）：
   - **属性不存在**（如 `--no-with-system-props` 未注入系统属性，或 `--unique-by` 指向的属性尚未创建）→ **跳过** `cc_ObjectUnique` 写入并输出告警（避免写入 `key_id` 为空的无效约束，C）；此时该模型实例导入将退为纯 INSERT（非幂等），需用户显式补建约束。
   - **属性存在** → 写入：
   ```sql
   INSERT OR REPLACE INTO cc_ObjectUnique
     (_id, id, bk_obj_id, keys, ispre, bk_supplier_account)
   VALUES
     (:_id, :id, :bk_obj_id, :keys, true, '0');
   ```
   其中 `:_id = "{bk_obj_id}_{key_prop}"`，`:id = generate_id()`，`:keys = JSON.stringify([{"key_kind":"property","key_id": key_attr_id}])`。
   > **说明**：键结构 `[{"key_kind":"property","key_id": <属性 id>}]` 与迁移脚本 `migrate.py` 完全一致（见 §5.8.4 的 upsert 键反查）。`--unique-by` 覆盖默认键时，须以该属性 `id` 重建 `cc_ObjectUnique`（即本步骤取该属性 `id`）。
   > **建模假设（E）**：默认以 `bk_inst_name` 唯一，意味着**同模型下两实例不能同名**（与真实 CMDB"实例名即标识"的惯例一致）。若某模型允许重名，请用 `--unique-by` 改键（如改用业务唯一编码属性），否则默认约束会阻断合法写入。

**完成后状态**：`GET /api/v1/models/{bk_obj_id}/attributes` 应返回 4 个系统属性；`GET /api/v1/models/{bk_obj_id}/instances` 返回空列表但可正常录入。

---

### 5.3 `cmdb attribute create`

为已有模型新增业务属性，并**同步修改实例分表结构**（对应指南 2.4 与属性类型→SQL 映射）。

**入参**

| 参数                                                           | 必填 | 说明                                      |
| ------------------------------------------------------------ | -- | --------------------------------------- |
| `--bk_obj_id`                                                | 是  | 目标模型 ID                                 |
| `--bk_property_id`                                           | 是  | 属性字段名（如 `status`），即实例表列名                |
| `--bk_property_name`                                         | 是  | 属性显示名（如 `状态`）                           |
| `--bk_property_type`                                         | 是  | 类型，见下方映射表                               |
| `--bk_property_group`                                        | 否  | 所属分组 ID（`bk_group_id`），默认 `default`；留空则配合 `--bk_group_name` 按显示名查/建 |
| `--bk_group_name`                                           | 否  | 分组显示名（`bk_group_name`）；给定且分组不存在时**自动建组**（随机 `bk_group_id`，见 §5.11.9） |
| `--isrequired`                                               | 否  | 是否必填，默认 `false`                         |
| `--editable`                                                 | 否  | 是否可编辑，默认 `true`                         |
| `--bk_ishidden` / `--bk_isapi` / `--bk_issystem` / `--ispre` | 否  | 各标志位，默认 `false`                         |
| `--bk_property_index`                                        | 否  | 排序，默认取该模型最大 index + 1                   |
| `--ismultiple`                                               | 否  | 多选（enummulti 需置 true），默认 `false`        |
| `--option`                                                   | 否  | JSON 字符串（enum/list/范围等，见指南 2.4 格式）      |
| `--placeholder` / `--unit`                                   | 否  | 占位符 / 单位                                |

> **分组解析（与 `attribute import` 一致，见 §5.11.9）**：通过 `resolve_or_create_group()` 按 `--bk_property_group`（ID）或 `--bk_group_name`（显示名）定位/创建分组；给定 `--bk_group_name` 且分组不存在时即触发自动建组（随机 `bk_group_id` + 该显示名）。仅当显式给出 `--bk_property_group` ID 且该 ID 必须新建时才校验 C1 白名单；自动建组生成的随机 ID 不受 C1 约束。

**执行步骤（事务内）**

1. **校验模型**：`SELECT 1 FROM cc_ObjDes WHERE bk_obj_id = :oid`，不存在报错。
2. **校验属性**：`SELECT 1 FROM cc_ObjAttDes WHERE bk_obj_id=:oid AND bk_property_id=:pid`，已存在则按 `--on-duplicate` 处理（`error` 默认报错退出，`skip` 跳过，`overwrite` 覆盖元数据）。
3. **写入属性定义**（对应指南 2.4）
   ```sql
   INSERT INTO cc_ObjAttDes
     (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type,
      bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
      bk_isapi, bk_issystem, ispre, ismultiple, bk_property_index, option,
      placeholder, unit, editable, bk_supplier_account)
   VALUES (...);
   ```
   > **ID 生成契约（C2）**：本行 `_id = "{bk_obj_id}.{bk_property_id}"`（如 `bk_switch.status`），`id = generate_id()`，与 §5.2 步骤 5 同一约定，保证 `cc_ObjAttDes` 主键唯一。
4. **ALTER 实例分表追加列**（关键差异点：模型创建时表只有系统列，属性需动态加列）
   ```sql
   ALTER TABLE "cc_ObjectBase_0_pub_{bk_obj_id}"
     ADD COLUMN "{bk_property_id}" {sql_type};
   ```
   > **标识符安全（C1）**：`{bk_obj_id}` 与 `{bk_property_id}` 来自用户输入，拼入 DDL 前须经 §1 白名单校验；`sql_type` 必须来自 `get_sql_type()` 的受控枚举，禁止透传原始类型字符串（防注入/非法类型）。
   > **已存在列探测（M5）**：SQLite 对重复列报 `duplicate column`；实现时应先 `PRAGMA table_info("cc_ObjectBase_0_pub_{bk_obj_id}")` 探测，列已存在则跳过加列（仅更新 `cc_ObjAttDes` 元数据），避免重跑失败。
   其中 `sql_type` 由 `get_sql_type(bk_property_type)` 决定：
   | bk_property_type                                                                | SQLite 列类型              | 备注                                           |
   | ------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------- |
   | int / long                                                                      | INTEGER / BIGINT        | —                                            |
   | singlechar / shortchar / char                                                   | VARCHAR                 | 短字符                                          |
   | longchar / text / textarea / enum / enummulti / list / objuser / array / object | TEXT                    | enum/enummulti/list/array/object 值为 JSON 字符串 |
   | float / double                                                                  | FLOAT / DOUBLE          | —                                            |
   | date / time / datetime                                                          | DATE / TIME / TIMESTAMP | —                                            |
   | bool / boolean                                                                  | BOOLEAN                 | —                                            |
5. **option 规范化**：若传入 `--option`，按指南 2.4 规范：enum 的 `is_default` 仅一个为 true；enummulti 须 `ismultiple=true`；简单数组经 `convert_enum_option()` 自动转标准格式；最终以 JSON 字符串存入 `option` 列。

**注意**：`id` / `bk_inst_id` / `bk_obj_id` 三类列已随模型创建生成，禁止再通过本命令创建。

---

### 5.4 `cmdb table create`

为**元数据已存在**（即 `cc_ObjDes` 已有记录）但实例表缺失的模型补建分表，等价于 `model create` 的步骤 6+7。

**入参**

| 参数                 | 必填 | 说明               |
| ------------------ | -- | ---------------- |
| `--bk_obj_id`      | 是  | 目标模型 ID          |
| `--skip-if-exists` | 否  | 表已存在则跳过（默认开启，幂等） |

**执行**：`CREATE TABLE IF NOT EXISTS` 建 `cc_ObjectBase_0_pub_{oid}` 与 `cc_InstAsst_0_pub_{oid}`，结构同 5.2 第 6、7 步。

**典型用途**：`model create` 误带 `--no-with-tables` 后补建；或迁移脚本未覆盖的遗留模型。

---

### 5.5 辅助命令（只读 / 反向）

| 命令                                | 说明                                                                                                                                                                                                                                      |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cmdb model show --bk_obj_id X`   | 输出模型元信息 + 分组列表 + 属性列表（用于复核，不影响数据）                                                                                                                                                                                                       |
| `cmdb model list`                 | 列出所有模型（含 `bk_ispaused` 状态）                                                                                                                                                                                                              |
| `cmdb model delete --bk_obj_id X` | 事务内：`DROP TABLE cc_ObjectBase_0_pub_X` + `DROP TABLE cc_InstAsst_0_pub_X` + `DELETE cc_ObjAttDes WHERE bk_obj_id=X` + `DELETE cc_PropertyGroup ...` + `DELETE cc_ObjectUnique ...` + `DELETE cc_ObjDes WHERE bk_obj_id=X`；危险操作需 `--yes` |

---

### 5.6 高级：`cmdb scaffold`（规格驱动）

读取一份 JSON/YAML 规格，一次创建「分类 + 模型 + 多属性」，内部顺序调用 5.1→5.2→5.3。此外提供 **CSV 模式**：通过 `seed` 生成带示例的 CSV 模板目录（§5.6.1），用户编辑后由 `apply` 批量执行（§5.6.2），等价于依次调用 §5.9/§5.10/§5.7/§5.8。

**规格示例（与指南 3.x 的前端 JSON 对齐）**

```json
{
  "classification": {
    "bk_classification_id": "bk_application",
    "bk_classification_name": "应用系统",
    "bk_classification_icon": "icon-cc-application",
    "ispre": true,
    "classification_index": 10
  },
  "model": {
    "bk_obj_id": "bk_application_system",
    "bk_obj_name": "应用系统",
    "bk_obj_icon": "icon-cc-application",
    "bk_classification_id": "bk_application",
    "ispre": false,
    "obj_sort_number": 0
  },
  "groups": [
    {"bk_group_id": "default", "bk_group_name": "默认", "bk_group_index": 0, "bk_isdefault": true},
    {"bk_group_id": "base",    "bk_group_name": "基础信息", "bk_group_index": 1, "bk_isdefault": false}
  ],
  "attributes": [
    {"bk_property_id": "name",       "bk_property_name": "名称",     "bk_property_type": "singlechar", "bk_property_group": "base", "isrequired": true,  "bk_property_index": 10, "placeholder": "请输入名称"},
    {"bk_property_id": "code",       "bk_property_name": "编码",     "bk_property_type": "singlechar", "bk_property_group": "base", "isrequired": true,  "bk_property_index": 11, "placeholder": "请输入编码"},
    {"bk_property_id": "status",     "bk_property_name": "状态",     "bk_property_type": "enum",       "bk_property_group": "base", "isrequired": false, "bk_property_index": 12,
      "option": [{"id":"running","name":"运行中","type":"text","is_default":true},
                 {"id":"stopped","name":"已停止","type":"text","is_default":false}]},
    {"bk_property_id": "environment", "bk_property_name": "所属环境", "bk_property_type": "list",       "bk_property_group": "base", "isrequired": false, "bk_property_index": 13,
      "option": ["生产环境","测试环境","开发环境"]},
    {"bk_property_id": "power_type",  "bk_property_name": "电源类型", "bk_property_type": "enummulti",  "bk_property_group": "default", "isrequired": false, "ismultiple": true, "bk_property_index": 14,
      "option": [{"id":"AC","name":"AC","type":"text","is_default":false},
                 {"id":"DC","name":"DC","type":"text","is_default":false}]},
    {"bk_property_id": "description", "bk_property_name": "描述",     "bk_property_type": "longchar",   "bk_property_group": "base", "isrequired": false, "bk_property_index": 15, "placeholder": "请输入描述"},
    {"bk_property_id": "bk_bakcup",   "bk_property_name": "备份状态", "bk_property_type": "bool",       "bk_property_group": "default", "isrequired": false, "bk_property_index": 16}
  ]
}
```

**字段说明**：

| 顶层键 | 作用 | 缺省行为 |
|--------|------|----------|
| `classification` | 新建/复用模型分类，写入 `cc_ObjClassification` | 可为空（不建分类）；若提供则**必须含 `bk_classification_id`，否则 spec 预检报错（退出码 `2`）**；可选 `classification_index`（整数，默认 `0`）控制分类显示顺序 |
| `model` | 模型元信息，写入 `cc_ObjDes` | 必需；**`bk_obj_id` 必填，缺则 spec 预检报错（退出码 `2`）**；`bk_ispaused` 固定写 `0` |
| `groups` | **属性分组定义**，写入 `cc_PropertyGroup` | **缺省时 CLI 自动创建 `default` 分组**（见 5.2 步骤 4）；显式给出则按规格创建（含 `base` 等） |
| `attributes` | 业务属性列表，逐条走 5.3 流程（写 `cc_ObjAttDes` + ALTER 实例表） | 每条属性按 `bk_property_group` 归入对应分组；类型经 `get_sql_type()` 映射为列类型 |

> 处理顺序：`classification` → `model`（自动补 4 个系统属性 + 实例表 + 关联表 + `default` 分组）→ `groups`（若显式给出则追加，与自动 `default` 去重）→ `attributes`（逐条加列）。
> 规格结构刻意与指南 3.3/3.4 的前端 `index.json`、`attributes/*.json` 保持一致，便于从前端定义直接转为 CLI 输入；其中 `option` 格式（enum 标准结构 / list 简单数组）与指南 2.4 完全一致。

> **spec 预检（退出码 `2`，§9）**：`scaffold spec` 解析 JSON 后**先校验必填字段**再开启事务：`model` 须为对象且含 `bk_obj_id`；若提供 `classification` 须含 `bk_classification_id`。缺失即 `CliError(EXIT_PARAM=2)` 终止，避免运行时 `TypeError` / `KeyError` 落到通用错误（退出码 `1`）；空文件 / 非法 JSON 已由 `parse_json` 返回 `None` 拦下并给 `EXIT_PARAM`。

#### 5.6.1 `cmdb scaffold seed`（CSV 模式：生成模板目录）

**背景**：面向"不想手写 JSON、直接填表"的场景。`seed` 在当前目录生成 `seed/<12位时间戳>/`，内含一套**已预填示例数据**的 CSV 模板（示例参考 `bk_switch` 与 `bk_deployment`，覆盖 enum / enummulti / list / bool / int / longchar 等多种 `option` 类型）。用户在此基础增删改后，再交给 `apply` 执行（§5.6.2）。所有生成文件格式分别与 §5.9 / §5.10 / §5.7 / §5.8 的导入命令**完全兼容**，也可单独用对应 import 命令执行。

**目录与文件名约定**

| 项 | 规则 |
|----|------|
| 根目录 | `./seed/`（可用 `--out-dir` 覆盖） |
| 时间戳目录名 | **12 位数字** `YYMMDDHHMMSS`（如 `260729001336`），由 `time.strftime("%y%m%d%H%M%S")` 生成，保证唯一且按时间排序 |
| 文件清单 | `classifications.csv` / `models.csv` / `attributes_<bk_obj_id>.csv`（每模型一个）/ `instances_<bk_obj_id>.csv`（每模型一个） |
| 兼容性 | 各文件格式 = §5.9 / §5.10 / §5.7 / §5.8 的输入契约；`attributes_*.csv` 采用 §5.7 的 3 行表头模板 |

**seed 生成的示例 CSV（参考 bk_switch + bk_deployment，覆盖多 option 类型）**

`classifications.csv`（对应 §5.9）：末列 `classification_index` 控制分类显示顺序（升序，缺省 `0`）。

```csv
bk_classification_id,bk_classification_name,bk_classification_icon,ispre,classification_index
bk_network,网络设备,icon-cc-network,false,1
bk_application,应用系统,icon-cc-application,false,2
```

`models.csv`（对应 §5.10）：

```csv
bk_obj_id,bk_obj_name,bk_classification_id,bk_obj_icon,ispre,bk_ishidden,bk_ispaused,obj_sort_number
bk_switch,交换机,bk_network,icon-cc-switch,false,false,false,0
bk_deployment,部署,bk_application,icon-cc-deployment,false,false,false,1
```

`attributes_bk_switch.csv`（对应 §5.7 的 3 行表头模板；覆盖 enum / enummulti / list / bool / int / longchar）：

```csv
英文名,中文名,数据类型,字段分组,数据配置,单位,描述,提示,是否可编辑,是否必填,是否只读,是否唯一,字段索引
string,string,enum,string,json,string,string,string,bool,bool,bool,bool,int
bk_property_id,bk_property_name,bk_property_type,bk_property_group,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
name,名称,singlechar,default,,,请输入名称,true,true,false,false,10
status,状态,enum,default,"[{""id"":""running"",""name"":""运行中"",""type"":""text"",""is_default"":true},{""id"":""stopped"",""name"":""已停止"",""type"":""text"",""is_default"":false}]",,状态,false,false,false,false,11
power_type,电源类型,enummulti,default,"[{""id"":""AC"",""name"":""AC"",""type"":""text"",""is_default"":false},{""id"":""DC"",""name"":""DC"",""type"":""text"",""is_default"":false}]",,电源,true,false,false,false,12
management_ip,管理IP,list,default,"[""192.168.1.1"",""192.168.1.2""]",,管理地址,true,false,false,false,13
port_count,端口数,int,default,,,,端口数量,true,false,false,false,14
bk_backup,是否备份,bool,default,,,,是否开启备份,true,false,false,false,15
description,描述,longchar,default,,,,设备描述,true,false,false,false,16
```

`attributes_bk_deployment.csv`（对应 §5.7；参考 deployment 模板的 dep_hosts / dep_ns / type，含 enum 示范）：

```csv
英文名,中文名,数据类型,字段分组,数据配置,单位,描述,提示,是否可编辑,是否必填,是否只读,是否唯一,字段索引
string,string,enum,string,json,string,string,string,bool,bool,bool,bool,int
bk_property_id,bk_property_name,bk_property_type,bk_property_group,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
dep_hosts,部署主机,singlechar,default,,,,部署目标主机,true,true,false,false,10
dep_ns,命名空间,singlechar,default,,,,K8s 命名空间,true,true,false,false,11
type,部署类型,enum,default,"[{""id"":""blue"",""name"":""蓝绿"",""type"":""text"",""is_default"":true},{""id"":""canary"",""name"":""金丝雀"",""type"":""text"",""is_default"":false}]",,部署策略,true,false,false,false,12
```

`instances_bk_switch.csv`（对应 §5.8；表头=实例表列，enum 存 `id`、enummulti/list 存 JSON 数组、bool 存 `1/0`）：

```csv
bk_inst_name,status,power_type,management_ip,port_count,bk_backup,description
核心交换机A,running,"[""AC""]","[""192.168.1.1"",""192.168.1.2""]",48,1,机房核心交换机
接入交换机B,stopped,"[""AC"",""DC""]","[""192.168.1.3""]",24,0,楼层接入
```

> **说明**：`instances_bk_deployment.csv` 按同样结构生成（表头取 `bk_deployment` 实例表列）。seed 仅为"参考示例 + 占位"，用户可整行删除、增改后再执行；仅含表头的空文件会被 `apply` 跳过而非报错。

> **生成契约（C1，RFC 4180）**：seed 写入端**必须**用合规 CSV 库以 `QUOTE_ALL` 包裹每个单元格（含逗号 / 引号的 `option`、`management_ip` JSON 单元格尤甚），确保 `apply` 的 RFC 4180 reader 能原样读回；用户手填编辑后也应保持双引号转义，否则 `apply` 解析会错列。

#### 5.6.2 `cmdb scaffold apply`（CSV 模式：批量执行目录内 CSV）

**命令与参数**

```bash
cmdb scaffold apply --dir <seed/12位时间戳> [options]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--dir` | 是 | `seed` 生成的目录（含上述 CSV 文件） |
| `--on-duplicate` | 否 | 全局重复策略，透传给各 import：`overwrite`（默认）/ `skip` |
| `--with-system-props` / `--with-tables` | 否 | 仅对 `models.csv` 生效（见 §5.10），默认开启 |
| `--atomic` / `--no-atomic` | 否 | 单事务开关（见 §5.11.4）；默认开启 |
| `--strict` | 否 | 任意文件/行失败即整体终止 |
| `--dry-run` | 否 | 仅打印各文件解析结果、映射与将执行的 SQL，不落库 |
| `--reject-out` / `--manifest-out` | 否 | 继承 §4 全局选项；拒绝汇写 `<dir>/<file>.rejects.csv`，运行清单写 `<dir>/.run.json`（见 §5.11.6 / §5.11.13） |

**文件识别与依赖顺序**

`apply` 扫描 `--dir` 内所有 `*.csv`，按文件名前缀归类，并**严格按依赖顺序**执行，避免"模型未建就导属性/实例"：

| 顺序 | 文件匹配 | 复用逻辑 | 说明 |
|------|----------|----------|------|
| 1 | `classifications.csv` | §5.9 classification import | 先建分类，供模型引用 |
| 2 | `models.csv` | §5.10 model import（`--with-system-props`/`--with-tables` 默认开） | 建模型 + 分组 + 系统属性 + 实例表/关联表 |
| 3 | `attributes_<bk_obj_id>.csv` | §5.7 attribute import | 从文件名提取 `bk_obj_id`；逐模型加属性并 ALTER 实例表 |
| 4 | `instances_<bk_obj_id>.csv` | §5.8 instance import | 从文件名提取 `bk_obj_id`；表头预检 + INSERT/UPSERT |

> 文件名中的 `<bk_obj_id>` 必须与 `models.csv` 中已存在的模型 ID 一致；`apply` 不依赖文件名之外的元信息。若某阶段文件缺失则跳过该阶段（如只导实例可不提供 `classifications.csv`）。

**执行步骤**

1. **扫描目录**：列出 `*.csv`，按上表顺序分组；无对应文件则跳过该阶段。
2. **预检门槛（H1）**：进入任一导入前，先输出各文件源画像（解析行数 / 检出列 / 样本 / 告警数，见 §5.11.1）；画像失败（空文件 / 表头 0 命中）直接退出码 `2`，不落库。
3. **逐阶段执行**：每阶段内部走对应 import 命令的完整流程（表头预检、类型校验、查重、写入、事务），并复用 §5.11 全部通用规范；坏行写入**拒绝汇**（§5.11.6，`<dir>/<file>.rejects.csv`）。
4. **阶段对账（H3）**：每阶段结束执行 §5.11.11 装载后对账，标记 `一致 ✓/✗`；任一阶段 `✗` 整体退出码取 `1`。
5. **跨阶段事务**：`--atomic` 下全部阶段包在**单个事务**（SQLite DDL 事务完全生效；PG/MySQL 退化为逐语句，见 §5.11.4 铁律）。
6. **运行清单（M3）**：全部结束后写出 `<dir>/.run.json`（含各文件 sha256 / 行数 / 参数 / `batch_id=seed/<ts>` / 时间戳，见 §5.11.13）。
7. **输出摘要**：各阶段 `新增/覆盖/跳过/失败/批内重复` 汇总 + 对账结论，JSON 或文本（§5.11.6）。

**示例**

```bash
# 1) 生成带示例的 seed 目录（12 位时间戳目录名）
python3 -m app.cli.cmdb scaffold seed --out-dir ./seed
# → 生成 ./seed/260729001336/{classifications,models,attributes_bk_switch,attributes_bk_deployment,instances_bk_switch}.csv

# 2)（用户编辑 CSV 后）先 dry-run 复核
python3 -m app.cli.cmdb scaffold apply --dir ./seed/260729001336 --dry-run

# 3) 正式执行：分类→模型→属性→实例，单事务
python3 -m app.cli.cmdb scaffold apply --dir ./seed/260729001336 --atomic
```

---

#### 5.6.3 `cmdb scaffold from-csv`（从实例 CSV 反向生成 seed 目录）

**背景**：面向"我手里已有一份现成的实例数据表（Excel 导出 / 外部系统 dump / 手填台账），想直接转成可 `apply` 的 CMDB 规格"的场景。用户给出一份 **首行为英文表头、其余行为实例数据** 的单模型 CSV，`from-csv` 据此**反向推导模型与属性规格**，生成与 `seed` 同构（§5.6.1）的 CSV 目录，用户可在生成结果上增改（如把某列类型从 `singlechar` 改为 `enum`、补 `option`、改 `isrequired`、`bk_obj_name`）后，直接 `scaffold apply`（§5.6.2）落库。与 §5.6.1 的区别：`seed` 提供"预填示例模板"，`from-csv` 提供"真实数据 + 自动推导的列规格"。

**命令与参数**

```bash
cmdb scaffold from-csv --csv <实例数据.csv> [options]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--csv` | 是 | 输入实例 CSV；**首行必须是英文表头，其余行为实例数据**；文件名 stem（去 `.csv` 后缀）作为模型 `bk_obj_id` |
| `--out-dir` | 否 | 输出根目录（默认 `./seed`），内部再建 12 位时间戳子目录（同 §5.6.1） |
| `--classification-id` | 否 | 生成的 `classifications.csv` 所用分类 ID；缺省 `bk_import` |
| `--classification-name` | 否 | 分类中文名；缺省 `分类-<id>` |
| `--model-name` | 否 | 模型中文名（`bk_obj_name`）；缺省 `模型-<bk_obj_id>` |
| `--dry-run` | 否 | 仅执行校验与推导、打印将生成的文件清单与样本，**不写盘**；**仍执行规则 1/2/2.1/4 全部校验，失败同样退出码 2** |
| `--json` | 否 | 以 JSON 输出问题报告 / 推导结果 |

**5 条硬性规则（全部满足才生成，否则中断零落盘）**

| # | 规则 | 校验器 | 失败处理 |
|---|------|--------|----------|
| 1 | CSV 文件名 stem → 模型名 `bk_obj_id`，**必须英文且匹配 `^[a-z][a-z0-9_]*$`** | `validate_identifier()`（同 §5.10 模型 ID 校验） | 计入问题记录，中断 |
| 2 | 表头每个英文 key → 属性 `bk_property_id`，**必须逐一匹配同一正则 `^[a-z][a-z0-9_]*$`**；不匹配即按规则 4 逐条记录并中断 | `validate_identifier()`（同 §5.7 属性 ID 校验） | 逐列出错点计入问题记录，中断 |
| 2.1 | **系统/保留列处理**（key 已通过规则 2 正则后判定）：`bk_inst_name` 属实例名，**允许原样保留**（既作属性 id 又作实例列，满足实例导入必填，不触发规则 4）；其余系统保留 id（`id`/`_id`/`bk_inst_id`/`bk_obj_id`/`bk_supplier_account`/`create_time`/`last_time`/`bk_operate_time`，见 `cmdb.py` 的 `SQLITE_SYSTEM_COLS`）**不拒绝**，而是对生成的 `bk_property_id` 与实例列**自动加前缀 `u_`** 区分（`u_`+原 key），避免 ALTER/upsert 覆盖系统列或类型冲突；若 `u_<key>` 仍与某表头 key 冲突则追加序号（`_2`/`_3`…） | 前缀映射表（key→`u_<key>`） | 属默认行为，不触发失败（`bk_inst_name` 例外、原样） |
| 3 | 推导出的每个属性 `bk_property_type` **默认为 `singlechar`**（不解析数据内容去推断类型；类型修正留给用户编辑后再 `apply`）；**中文属性名 `bk_property_name` 默认用同一英文 key 原值补填**（同源填充，便于后续改中文） | 固定写 `singlechar` + `bk_property_name=英文key` | 属默认行为，不触发失败 |
| 3.1 | 实例表必填列 `bk_inst_name` 若不在表头中，则**强制补入**：属性表加一条 `singlechar / isrequired=true`，并在生成 `instances_<oid>.csv` 表头前置 `bk_inst_name` 列、数据行以 `bk_<obj_id>_<行号>` 占位，确保 `apply` 的实例导入不报必填缺失 | — | 属默认行为，不触发失败 |
| 4 | 规则 1/2 任一不通过 → **全量扫描收集全部问题 → 输出问题记录报告 → 退出码 2，不生成任何文件** | 先校验再写盘 | 中断、零落盘 |
| 5 | 校验通过 → 输出与 `seed` 同构的目录（12 位时间戳子目录 + 同名 CSV 文件），可被 `scaffold apply` 直接消费 | 复用 §5.6.1 文件契约 | 落盘 |

> **关键约束（C2，标识符同源）**：`bk_obj_id` 与 `bk_property_id` 共用同一个白名单正则 `IDENTIFIER_RE = re.compile(r'^[a-z][a-z0-9_]*$')`（见 `app/cli/safety.py`），因此规则 1、2 本质是"同一校验器分别作用于文件名 stem 与每个表头列"。校验为**严格匹配、不做隐式转换**（大写不自动转小写、非法字符不自动剔除），不通过即按规则 4 中断，由用户改名/改列后重试。

> **生成契约（C1，RFC 4180）**：与 §5.6.1 一致，`from-csv` 写入端**必须**用合规 CSV 库以 `QUOTE_ALL` 包裹每个单元格，确保 `apply` 的 RFC 4180 reader 原样读回（§5.6.2）。

**校验与中断流程**

1. **解析 CSV**：以 RFC 4180 读入（同 `read_csv_rows`，`utf-8-sig` 兼容带 BOM）；若无法解析或无数据行则按规则 4 出报告。
2. **表头存在性 / 归一**：首行必须非空且全部为英文标识；空表头行 → 问题记录 `文件无有效表头`；每个 key 先 `strip()` 首尾空格（避免 `' ip'` 之类因空格触发规则 2 失败）。
3. **模型名校验（规则 1）**：对文件名 stem 调 `validate_identifier()`，失败记 `文件名 stem '<stem>' 不符合 ^[a-z][a-z0-9_]*$`。
4. **属性名正则校验（规则 2）**：对表头每个 key 调 `validate_identifier()`，失败按 `第 N 列 '<key>' 不符合属性 ID 正则` 逐条记录（含列序号，便于定位）。
4.1 **系统/保留列处理（规则 2.1）**：key 通过规则 2 后，`bk_inst_name` 原样保留；其余命中 `SQLITE_SYSTEM_COLS` 的 key（`id`/`_id`/`bk_inst_id`/`bk_obj_id`/`bk_supplier_account`/`create_time`/`last_time`/`bk_operate_time`）生成前缀映射 `u_<key>`，并记录到「前缀映射表」（用于生成阶段同时改写属性 id 与实例列名）；若 `u_<key>` 仍与某表头 key 冲突则追加序号。
5. **去重校验**：表头存在重复 key（同一英文 key 出现 ≥2 次）→ 记录 `表头重复列 '<key>'`，按规则 4 中断；`bk_inst_name` 与系统保留列已在规则 2.1 单独处理，不在此判重。
6. **汇总判定（规则 4）**：若问题列表非空 → 打印**问题记录报告**（见下表），退出码 `2`，**不创建任何目录、不写任何文件**；列表为空才进入生成。
7. **生成（规则 5）**：按下方「生成文件集」写盘；`--dry-run` 仍执行以上全部校验，失败时同样退出码 2 且不写盘，仅打印镜像结果。

**问题记录报告格式（校验失败时输出）**

```text
[from-csv] 校验未通过，已中断（退出码 2），未生成任何文件。
源文件: /path/to/Servers.csv
问题记录:
  [规则1] 文件名 stem 'Servers' 不符合 ^[a-z][a-z0-9_]*$（需小写字母开头、仅含小写字母/数字/下划线）
  [规则2] 第 3 列 'IP 地址' 不符合属性 ID 正则（含中文/空格）
  [规则2] 第 5 列 '1st_field' 不符合属性 ID 正则（数字开头）
请修正后重试。
```

**生成文件集（与 seed 同构，§5.6.2 `apply` 直读）**

| 文件 | 对应章节 | 内容 |
|------|----------|------|
| `classifications.csv` | §5.9 | 1 行：`bk_classification_id`（`--classification-id`，缺省 `bk_import`）/ `bk_classification_name` / `bk_classification_icon`（`icon-cc-default`）/`ispre=false` / `classification_index=0`（缺省 `0`） |
| `models.csv` | §5.10 | 1 行：`bk_obj_id`（文件名 stem）/ `bk_obj_name`（`--model-name` 或 `模型-<id>`）/ `bk_classification_id` / `bk_obj_icon`（`icon-cc-default`）/ `ispre=false` / `bk_ishidden=false` / `bk_ispaused=false` / `obj_sort_number=0` |
| `attributes_<oid>.csv` | §5.7 | **3 行表头（14 列 seed 模板，含新增 `bk_group_name`）**；每表头 key 一行：**中文名 `bk_property_name` 默认 = 该英文 key 原值**（同源补填）、`bk_property_type=singlechar`、`bk_property_group=default`、`bk_group_name=''`、`editable=true`、`isrequired=false`（`bk_inst_name` 为 `true`）、其余缺省 `false/0`；`bk_property_index` 从 10 递增（`bk_inst_name` 固定 10，与 seed 模板的 `0` 不同，仅影响展示顺序）；**系统保留 key 按规则 2.1 改写 `bk_property_id = u_<key>`**（中文名仍取原 key） |
| `instances_<oid>.csv` | §5.8 | **单行英文表头** = 输入表头（规则 3.1 缺 `bk_inst_name` 时前置该列；规则 2.1 系统保留 key 同步改写为 `u_<key>`，数据随列名迁移），数据行原样回写（`QUOTE_ALL`）；因全部 `singlechar`，单元值即字符串，无需类型归一 |

> `attributes_<oid>.csv` 采用 §5.6.1 的 14 列 seed 模板（含新增 `bk_group_name` 分组显示名列，而非 §5.7.3 的 17 列 export 模板），与 `apply` 兼容（§5.6.2 已确认 import/apply 同时接受 seed-14 与 export-17 两种结构）。`description` 列在 seed 模板中存在但 `from-csv` 不产出内容（留空供编辑），符合 §5.7 对 `description` 列的"读取即丢弃"约定。

**示例**

输入 `servers.csv`（首行英文表头 + 实例数据）：

```csv
bk_inst_name,ip,region,owner
web-01,10.0.0.1,sh,alice
web-02,10.0.0.2,bj,bob
```

命令与输出：

```bash
# 反向推导 + 生成 seed 同构目录（12 位时间戳目录名）
python3 -m app.cli.cmdb scaffold from-csv --csv servers.csv --classification-id bk_application
# → 生成 ./seed/260805002341/{classifications,models,attributes_servers,instances_servers}.csv
```

生成的 `attributes_servers.csv`（3 行表头，14 列，全部 `singlechar`；`bk_inst_name` 必填）：

```csv
英文名,中文名,数据类型,字段分组,数据配置,单位,描述,提示,是否可编辑,是否必填,是否只读,是否唯一,字段索引
string,string,enum,string,json,string,string,string,bool,bool,bool,bool,int
bk_property_id,bk_property_name,bk_property_type,bk_property_group,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
bk_inst_name,bk_inst_name,singlechar,default,,,,true,true,false,false,10
ip,ip,singlechar,default,,,,true,false,false,false,11
region,region,singlechar,default,,,,true,false,false,false,12
owner,owner,singlechar,default,,,,true,false,false,false,13
```

生成的 `instances_servers.csv`（表头回映输入，数据原样）：

```csv
bk_inst_name,ip,region,owner
web-01,10.0.0.1,sh,alice
web-02,10.0.0.2,bj,bob
```

规则 3.1 触发示例（表头缺 `bk_inst_name`，自动补列）：

```csv
# 输入 missing_name.csv（无 bk_inst_name 列）
ip,region
10.0.0.1,sh
```
```bash
python3 -m app.cli.cmdb scaffold from-csv --csv missing_name.csv
# attributes_missing_name.csv 中自动补 bk_inst_name(singlechar/isrequired=true, index=10)
# instances_missing_name.csv 表头前置 bk_inst_name，数据行填 bk_missing_name_1 / bk_missing_name_2
```

规则 2.1 触发示例（表头含系统保留列，自动加前缀区分，不拒绝）：

```csv
# 输入 with_sys.csv（含 bk_obj_id、id 等系统保留列）
bk_inst_name,ip,bk_obj_id,id
srv-01,10.0.0.1,app,1001
srv-02,10.0.0.2,db,1002
```
```bash
python3 -m app.cli.cmdb scaffold from-csv --csv with_sys.csv
# 前缀映射表：bk_obj_id -> u_bk_obj_id；id -> u_id（均为业务属性，不触碰系统列）
# attributes_with_sys.csv：bk_property_id 改写为 u_bk_obj_id / u_id（中文名仍为 bk_obj_id / id）
# instances_with_sys.csv 表头同步改写为 bk_inst_name,ip,u_bk_obj_id,u_id，数据随列名迁移
```

随后用户编辑（如把 `region` 改为 `enum` 并补 `option`）即可：

```bash
python3 -m app.cli.cmdb scaffold apply --dir ./seed/260805002341 --atomic
```

---


### 5.7 `cmdb attribute import`（CSV 批量导入属性）

**背景**：原项目提供属性描述导入模板（CSV），其列结构为
`英文名 / 中文名 / 数据类型 / 字段分组 / 数据配置 / 单位 / 描述 / 提示 / 是否可编辑 / 是否必填 / 是否只读 / 是否唯一 / 字段索引`（对应 Excel A~M 列）。
本命令以该 CSV 为输入，批量**创建或更新**模型属性，并同步 `ALTER` 实例分表追加物理列。

#### 5.7.1 CSV 列 → 属性字段映射（含 F~M 实现现状确认）

模板前 3 行为说明行（中文名 / 类型 / 英文字段名），**以首单元格为 `bk_property_id` 的行为表头，其下为数据行**。

| CSV 列 | 中文 | 属性字段 | DB | API | UI | 导入处理策略 |
|--------|------|----------|----|-----|----|--------------|
| A | 英文名(必填) | `bk_property_id` | — | — | — | 主键，必填；用于"同 id 覆盖 / 异 id 新增"判定 |
| B | 中文名(必填) | `bk_property_name` | — | — | — | 必填 |
| C | 数据类型(必填) | `bk_property_type` | — | — | — | 经 `get_sql_type()` 校验，必须在 16 种合法类型内 |
| D | 字段分组 | `bk_property_group` | ✅ | ✅ | ✅ | **分组 ID**（`bk_group_id`）；可空，缺省 `default`。与 `bk_group_name` 共同决定分组归属（见 §5.11.9） |
| **新增列** | 分组显示名 | `bk_group_name` | ✅ | ✅ | ✅ | **分组显示名**（`bk_group_name`），可空。与 D 列配合：`--group-auto-create` 时按显示名去重自动建组（随机 `bk_group_id`）；命中已有分组（按 ID 或显示名）则复用 |
| E | 数据配置 | `option` | ✅ | ✅ | ✅ | enum/enummulti/list 解析 JSON；list 简单数组经 `convert_enum_option()` |
| **F** | 单位 | `unit` | ✅ | ✅ | ✅ | 直接写入（`int.vue`/`float.vue` 作单位后缀） |
| **G** | 描述 | `description` | ❌ | ❌ | ❌ | **lite 三层均未实现**；默认丢弃并告警；本 CLI **不提供补齐开关**（加列会产生 API/UI 不消费的孤儿数据，见 H2） |
| **H** | 提示 | `placeholder` | ✅ | ✅ | ✅ | 直接写入（表单输入占位符） |
| **I** | 是否可编辑 | `editable` | ✅ | ✅ | ✅ | `TRUE/FALSE` → `1/0` |
| **J** | 是否必填 | `isrequired` | ✅ | ✅ | ✅ | `TRUE/FALSE` → `1/0`（表单校验） |
| **K** | 是否只读 | `isreadonly` | ✅ | ✅ | ✅ | `TRUE/FALSE` → `1/0`（表单禁用） |
| **L** | 是否唯一 | `isonly` | ✅* | ✅ | ⚠️ | `TRUE/FALSE` → `1/0`；\*列存在但语义已废弃，唯一性改由 `cc_ObjectUnique` 承担，可 `--create-unique` 生成约束 |
| **M** | 字段索引 | `bk_property_index` | ✅ | ✅ | ✅ | 整型，用于属性排序（前端 `bk_property_index >= 0` 过滤） |

> **确认结论（问题 1）**：F~M 共 8 列中，**仅 G 列「描述 / `description`」在 lite 的 DB（无列）、API（`SELECT *` 不返回）、UI（无对应字段）三层均未实现**；其余 7 列（unit / placeholder / editable / isrequired / isreadonly / isonly* / bk_property_index）均已落地。`isonly` 虽列存在，但按指南八规则已"不再使用"，唯一性由 `cc_ObjectUnique` 实现，导入时仅落库该标志位。
>
> **原项目溯源（bk-cmdb 上游）**：原项目 `Attribute` 结构体（`src/common/metadata/attribute.go:129`）**声明了** `Description` 字段，且其模型属性 Excel 导入模板（`src/web_server/service/excel/operator/model/operator.go:162`）**将 `description` 列为导入字段**——你这份 CSV 模板正是该导入模板的转写（F~M 列顺序与原文 `fields` 列表完全一致）。但原项目在升级脚本 `x19.04.16.01/removeDescriptionField.go` 中已 `DropColumn("description")` 从 `cc_ObjAttDes` **删除该存储列且后续未再加回**，原项目前端字段管理（`field-group`）也不暴露 `description`。**故 lite 不实现 `description` 并非缺失，而是与原项目 `cc_ObjAttDes` 的"有效现状"保持一致**——该列在原项目中同样是"模板声明但存储已删"的历史遗留。这正是 §5.7.2 **默认丢弃 G 列、且不提供补齐开关**（避免产生 API/UI 不消费的孤儿数据）的设计依据。

#### 5.7.2 命令设计

```bash
cmdb attribute import --csv <path> --bk_obj_id <model> [options]
```

**入参**

| 参数 | 必填 | 说明 |
|------|------|------|
| `--csv` | 是 | CSV 文件路径（原项目属性描述导入模板） |
| `--bk_obj_id` | 是 | 目标模型 ID（需已存在；若不存在先报"模型不存在"） |
| `--encoding` | 否 | 文件编码，默认 `utf-8` |
| `--delimiter` | 否 | 分隔符，默认 `,` |
| `--on-duplicate` | 否 | 重复策略：`overwrite`（默认，同 `bk_property_id` 覆盖）/ `skip`（跳过已存在） |
| `--atomic` / `--no-atomic` | 否 | **事务开关（问题 2 核心）**：所有写入与 `ALTER` 是否包在**同一事务**；默认开启（`--atomic`） |
| `--group-auto-create` | 否 | 分组（按 `bk_property_group` ID 或 `bk_group_name` 显示名）不存在时**自动创建**：给定 `bk_group_name` 则生成随机 `bk_group_id`（`generate_group_id()`）并以该显示名命名；仅给 `bk_property_group` ID 则按该 ID 建组（须过 C1 白名单），显示名取 `KNOWN_GROUP_NAMES` 兜底 |
| `--create-unique` | 否 | 当 L 列 `isonly=TRUE` 时，同步向 `cc_ObjectUnique` 写入单字段唯一约束 |
| `--strict` | 否 | 任意行校验失败即整体终止（默认仅跳过该行并计入错误清单） |
| `--dry-run` | 否 | 仅打印将执行的 SQL 与映射结果，不落库 |

**执行步骤**

1. **定位表头**：扫描首单元格为 `bk_property_id` 的行作为字段名行，其下为数据行。
2. **逐行处理**（校验：`bk_property_id` / `bk_property_name` / `bk_property_type` 必填且类型合法，否则按 `--strict` 决定跳过或终止）：
   - 解析布尔列 I/J/K/L（`TRUE/FALSE` → `1/0`）；解析 E 列 `option`（enum/list 经 `convert_enum_option()`）；
   - 解析分组（`bk_property_group` = 分组 ID，`bk_group_name` = 显示名）：经 `resolve_or_create_group()` 按"ID 精确匹配 → 显示名去重复用 → `--group-auto-create` 建组"顺序得出最终 `bk_group_id`（见 §5.11.9）；给定 `bk_group_name` 时自动建组生成随机 ID，同一显示名在导入批次内去重复用同一 ID，默认归 `default`；
   - G 列 `description`：lite 三层均未实现该列（与上游一致），**默认丢弃并告警**；本 CLI 不提供补齐开关（加列会产生 API/UI 不消费的孤儿数据，见 H2），若项目确需应在 API/UI 端到端支持后由迁移脚本加列；
   - **查重**：`SELECT 1 FROM cc_ObjAttDes WHERE bk_obj_id=:oid AND bk_property_id=:pid`
     - 存在 + `overwrite` → `UPDATE` 全部可写字段；若类型变化，SQLite 下 `ALTER COLUMN` 能力有限，默认不改列类型并提示；
     - 存在 + `skip` → 跳过；
     - 不存在 → `INSERT` 新属性 + `ALTER "cc_ObjectBase_0_pub_{oid}" ADD COLUMN "{bk_property_id}" {sql_type}`（`sql_type` 来自 `get_sql_type()`；enum/enummulti/list/object/array → `TEXT`）。
3. **事务开关（`--atomic`，默认开）**：
   - `--atomic`：把"全部 `INSERT/UPDATE cc_ObjAttDes` + 全部 `ALTER` 实例表"包在**单个事务**；任一失败整体回滚。
   - `--no-atomic`：逐行提交，允许部分成功；失败行仅跳过并记入错误清单。
   - ⚠️ 跨库说明：SQLite 支持 DDL 事务（原子性完全生效）；PostgreSQL / MySQL 的 DDL 会隐式提交，`--atomic` 退化为"逐语句尽力提交"，原子性不保证。
4. **输出摘要**：新增 N / 覆盖 M / 跳过 K / 失败 F / `description` 丢弃 P（JSON 或文本）；坏行见拒绝汇（§5.11.6），落库后执行对账（§5.11.11）。

> **标识符安全（C1）**：步骤 2 中 `ALTER "cc_ObjectBase_0_pub_{oid}" ADD COLUMN "{bk_property_id}"` 的 `{oid}` 与 `{bk_property_id}` 来自 CSV/用户输入，拼入 DDL 前须经 §1 白名单校验；`sql_type` 必须来自 `get_sql_type()` 受控枚举，禁止透传原始类型字符串。

**示例**

```bash
# 原子模式（默认）：同 bk_property_id 覆盖、异则新增，所有 ALTER 在同一事务
python3 -m app.cli.cmdb attribute import \
  --csv ./bk_cmdb_model_deployment.csv \
  --bk_obj_id bk_deployment \
  --on-duplicate overwrite \
  --atomic

# 非原子模式 + 自动建分组与唯一约束（宽松导入；description 列按默认丢弃并告警）
python3 -m app.cli.cmdb attribute import \
  --csv ./bk_cmdb_model_deployment.csv \
  --bk_obj_id bk_deployment \
  --no-atomic --create-unique --group-auto-create
```

**两列分组 + 显示名去重示例**（CSV 14 列，D=`bk_property_group`、新增 E=`bk_group_name`）：

```csv
bk_property_id,bk_property_name,bk_property_type,bk_property_group,bk_group_name,option,unit,description,placeholder,editable,isrequired,isreadonly,isonly,bk_property_index
ip,IP,singlechar,network,网络配置,,,,,,true,false,false,false,10
port,端口,int,network,网络配置,,,,,,false,false,false,false,11
remark,备注,longchar,,网络配置,,,,,,false,false,false,false,12
```

```bash
# 三条属性均填 bk_group_name=网络配置：--group-auto-create 时仅建一个随机 bk_group_id，
# 三条属性共享该 ID（按显示名去重，镜像上游 grpNameIDMap）；remark 未填 ID 也按显示名归同组
python3 -m app.cli.cmdb attribute import \
  --csv ./grp_demo.csv --bk_obj_id bk_deployment --group-auto-create
```

---

### 5.8 `cmdb instance import`（CSV 批量导入实例）

**背景**：与 §5.7（导入属性**定义**）不同，本命令把 CSV **逐行写入实例分表** `cc_ObjectBase_0_pub_{bk_obj_id}`。CSV **第 1 行必须是表头（header）**，表头单元格即目标表的列名（业务属性用 `bk_property_id`，系统列可用 `bk_inst_name` / `bk_inst_id` 等）。

**核心规则（用户要求）**：
- **表头预检**：读第 1 行，与实例表实际列做匹配预检；表头列必须在表内（系统列或已定义属性列），未知列报错（除非 `--skip-unknown-columns`）。
- **无唯一组合 → 仅插入（INSERT）**：若模型在 `cc_ObjectUnique` 中**无任何唯一约束记录**，则每行直接 `INSERT`（实例标识 `bk_inst_id` 缺失时由 `generate_id()` 生成）。
- **有唯一组合 → UPSERT**：若 `cc_ObjectUnique` 存在约束，则以约束涉及的属性列作为匹配键；命中则 `UPDATE`、未命中则 `INSERT`。

#### 5.8.1 命令与参数

```bash
cmdb instance import --csv <path> --bk_obj_id <model> [options]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--csv` | 是 | CSV 文件路径（**第 1 行为表头**） |
| `--bk_obj_id` | 是 | 目标模型 ID；实例表 = `cc_ObjectBase_0_pub_{oid}` |
| `--encoding` | 否 | 文件编码，默认 `utf-8`（自动剔除 BOM） |
| `--delimiter` | 否 | 分隔符，默认 `,`（支持 `\t`） |
| `--mode` | 否 | `auto`（默认，按 `cc_ObjectUnique` 自动判定）/ `insert`（强制仅插入）/ `upsert`（强制 upsert） |
| `--upsert-key` | 否 | 导入时显式指定 upsert 匹配列（逗号分隔，如 `bk_inst_name,management_ip`），覆盖从 `cc_ObjectUnique` 的自动判定（注意：与 `model create` 的 `--unique-by` 定键语义不同） |
| `--atomic` / `--no-atomic` | 否 | **事务开关**（同 §5.7）：全部写操作包在同一事务；默认开启 |
| `--generate-inst-id` | 否 | 插入时若行内无 `bk_inst_id` 则自动 `generate_id()` 生成（默认开） |
| `--enum-by-name` | 否 | enum/enummulti 单元格按显示名（而非 `id`）匹配 `option`，自动解析为 `id` |
| `--multivalue-sep` | 否 | list/enummulti/array 单元格的多值分隔符，默认 `,`，用于把 `a,b,c` 转 JSON 数组 |
| `--skip-unknown-columns` | 否 | 表头中存在但实例表不存在的列，跳过该列（默认报错） |
| `--truncate` | 否 | 导入前清空实例表（危险，需 `--yes`） |
| `--batch-size` | 否 | 非原子模式下每批提交行数，默认 `500` |
| `--dry-run` | 否 | 仅打印映射与将执行的 SQL，不落库 |

#### 5.8.2 执行步骤

1. **解析表头（强制）**：读第 1 行作为 header；若为空或无法解析 → 退出码 `2`。
2. **目标表与列集**：确认 `cc_ObjDes` 中模型存在且 `cc_ObjectBase_0_pub_{oid}` 表存在；汇总"允许写入列" = 系统可写列（`bk_inst_name`、`bk_inst_id` 等）+ 该模型 `cc_ObjAttDes` 中业务属性列（按 §5.3 过滤：`bk_isapi=false` 且非隐藏）。
   > **标识符安全（C1）**：`{oid}` 来自 `--bk_obj_id` 参数，拼入表名 `cc_ObjectBase_0_pub_{oid}` 前须经 §1 白名单校验；表头列名经步骤 3 与实例表实际列严格比对（命中才纳入），故不会把未知标识符拼入 `INSERT` 列清单。
3. **表头预检**：逐个 header 列比对"允许写入列"；
   - 命中 → 纳入映射；
   - 未命中 → 默认报错退出（退出码 `2`），除非 `--skip-unknown-columns` 跳过该列；
   - 强约束：`bk_inst_name` 应在表头内（实例名称必填），缺失且无值则跳过/报错该行。
4. **判定模式**：
   - `auto`：`SELECT keys FROM cc_ObjectUnique WHERE bk_obj_id=:oid`；有记录 → **upsert 模式**，匹配列 = 约束 `keys` 中的 `key_id` 经 `cc_ObjAttDes.id` 反查出的 `bk_property_id`（多约束取并集）；无记录 → **insert 模式**；
   - 显式 `--upsert-key` / `--mode` 覆盖自动判定；
   - upsert 模式要求匹配列均在表头内，否则预检报错。
5. **逐行处理（类型转换）**：
   - 按 header 映射单元格 → 列值；
   - `int`/`float` 数值化；`bool` `TRUE/FALSE`→`1/0`；`date`/`datetime` 解析；
   - 复合类型（`enum`/`enummulti`/`list`/`object`/`array`）：`enum` 存 `option` 中的 `id`（`--enum-by-name` 时按 `name` 反查）；`list`/`enummulti`/`array` 单元格若为 JSON 串原样存，否则按 `--multivalue-sep` 拆成 JSON 数组字符串；`object` 存 JSON 串；
   - 注入系统列：`bk_obj_id=:oid`、`bk_supplier_account='0'`；`bk_inst_id` 缺失则 `generate_id()`；`id` 同 `bk_inst_id`；`create_time`/`last_time` 默认 `CURRENT_TIMESTAMP`；
   - **insert 模式**：`INSERT INTO "cc_ObjectBase_0_pub_{oid}" (cols) VALUES (...)`；
   - **upsert 模式**：`SELECT 1 FROM "cc_ObjectBase_0_pub_{oid}" WHERE k1=:v1 AND k2=:v2 ...` → 命中 `UPDATE` 非标识列（排除 `id`/`bk_inst_id`/`bk_obj_id`），未命中 `INSERT`（含生成 `bk_inst_id`）。
6. **事务开关（`--atomic` 默认开）**：同 §5.7.2 第 3 点（SQLite 支持写事务原子性；PG/MySQL 退化为逐语句）。
7. **输出摘要**：插入 N / 更新 M / 跳过 K / 失败 F（含未知列、类型错误、唯一冲突）/ 批内重复 D；坏行见拒绝汇（§5.11.6）；落库后执行对账（§5.11.11）。

**示例**

```bash
# 自动模式：有唯一约束则 upsert、无则 insert；表头须匹配实例表列
python3 -m app.cli.cmdb instance import \
  --csv ./bk_switch_instances.csv \
  --bk_obj_id bk_switch --mode auto --atomic

# 强制 upsert + 显式匹配键 + 枚举按名称解析 + 多值分隔符
python3 -m app.cli.cmdb instance import \
  --csv ./bk_switch_instances.csv \
  --bk_obj_id bk_switch --mode upsert \
  --upsert-key bk_inst_name,management_ip \
  --enum-by-name --multivalue-sep ';'
```

---

### 5.9 `cmdb classification import`（CSV 批量导入模型分类）

**背景**：将多个模型分类从 CSV 一次性写入 `cc_ObjClassification`，等价于对 §5.1 的循环执行。适用于初始化一批业务分类（如"网络设备 / 安全设备 / 应用系统"）。所有写操作遵循 §5.11 通用规范。

**CSV 列映射**

| CSV 列 | 属性字段 | 必填 | 说明 |
|--------|----------|------|------|
| 分类ID | `bk_classification_id` | 是 | 唯一；分类不存在则写入，已存在按 `--on-duplicate` 处理 |
| 分类名称 | `bk_classification_name` | 是 | 前端导航显示 |
| 图标 | `bk_classification_icon` | 否 | 默认 `icon-cc-default` |
| 是否预置 | `ispre` | 否 | `TRUE/FALSE` → `1/0`，默认 `0` |
| 排序序号 | `classification_index`（别名：`index`/`排序`/`排序序号`/`sort_index`/`索引`） | 否 | 整数，默认 `0`；写入 `cc_ObjClassification.classification_index`，决定资源目录分类显示顺序（升序，越小越靠前）。缺列/空值/非法值统一回退 `0` |

**命令与参数**

```bash
cmdb classification import --csv <path> [options]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--csv` | 是 | CSV 文件路径（第 1 行为表头，列名见上表） |
| `--encoding` | 否 | 默认 `utf-8`（自动剔 BOM，见 §5.11.1） |
| `--delimiter` | 否 | 默认 `,` |
| `--on-duplicate` | 否 | `overwrite`（默认，同 `bk_classification_id` 覆盖）/ `skip`（跳过已存在） |
| `--atomic` / `--no-atomic` | 否 | 单事务开关（同 §5.7.2）；默认开启 |
| `--strict` | 否 | 任意行校验失败即整体终止（默认仅跳过并记录错误清单） |
| `--dry-run` | 否 | 仅打印映射与 SQL，不落库 |

**执行步骤**

1. **解析表头**（§5.11.2 表头契约）：首行列名须命中映射表，否则退出码 `2`。
2. **逐行校验**：`bk_classification_id` / `bk_classification_name` 必填，否则按 `--strict` 跳过或终止。
3. **查重**：`SELECT 1 FROM cc_ObjClassification WHERE bk_classification_id=:cid`
   - 不存在 → `INSERT`（`id` 缺省取 `MAX(id)+1`，`bk_supplier_account='0'`）；
   - 存在 + `overwrite` → `UPDATE bk_classification_name / bk_classification_icon / ispre`；
   - 存在 + `skip` → 跳过。
4. **事务开关**（§5.11.4）：分类导入为纯 DML，`--atomic` 下全部写入包在单事务；PG/MySQL 下原子性同样生效（无 DDL 隐式提交问题）。
5. **输出摘要**：新增 N / 覆盖 M / 跳过 K / 失败 F（JSON 或文本，见 §5.11.6）。

**示例**

```bash
python3 -m app.cli.cmdb classification import \
  --csv ./classifications.csv --on-duplicate overwrite --atomic
```

---

### 5.10 `cmdb model import`（CSV 批量导入模型）

**背景**：将多个模型从 CSV 一次性写入 `cc_ObjDes`，并可按 §5.2 的"完整创建"路径，为每个模型**连带生成 Default 分组、4 个系统属性、实例分表、关联分表**，达到"导入即可在前端看到并录入实例"的状态。等价于对 §5.2 的循环执行。所有写操作遵循 §5.11 通用规范。

**CSV 列映射**

| CSV 列 | 属性字段 | 必填 | 说明 |
|--------|----------|------|------|
| 模型ID | `bk_obj_id` | 是 | 唯一主键；须与实例表名 `cc_ObjectBase_0_pub_{bk_obj_id}` 一致 |
| 模型名称 | `bk_obj_name` | 是 | 前端显示 |
| 所属分类 | `bk_classification_id` | 是 | 须已在 `cc_ObjClassification` 存在，否则该行报错/跳过 |
| 模型图标 | `bk_obj_icon` | 否 | 默认 `icon-cc-default` |
| 是否预置 | `ispre` | 否 | `TRUE/FALSE`→`1/0`，默认 `0` |
| 是否隐藏 | `bk_ishidden` | 否 | 默认 `0` |
| 是否停用 | `bk_ispaused` | 否 | 默认 `0` |
| 排序号 | `obj_sort_number` | 否 | 整型，默认 `0` |

**命令与参数**

```bash
cmdb model import --csv <path> [options]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--csv` | 是 | CSV 文件路径（第 1 行为表头） |
| `--encoding` / `--delimiter` | 否 | 同 §5.9 |
| `--on-duplicate` | 否 | `overwrite`（默认）/`skip`；覆盖时仅更新 `cc_ObjDes` 元数据，不重建系统属性与表 |
| `--with-system-props` | 否 | 新建模型时是否注入 4 个系统属性，默认开启 |
| `--with-tables` | 否 | 新建模型时是否建实例表 + 关联表，默认开启 |
| `--atomic` / `--no-atomic` | 否 | 单事务开关；每模型创建包在各自事务内，默认开启（§5.11.4） |
| `--strict` | 否 | 任意行失败即整体终止 |
| `--dry-run` | 否 | 仅打印映射与 SQL，不落库 |

**执行步骤**

1. **解析表头**（§5.11.2）：首行列名须命中映射表，否则退出码 `2`。
2. **逐行校验**：`bk_obj_id` / `bk_obj_name` / `bk_classification_id` 必填；分类须存在（否则该行报错/跳过）。
3. **查重**：`SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:oid`
   - 存在 + `overwrite` → `UPDATE` 元数据（`bk_obj_name`/`bk_obj_icon`/`ispre`/`bk_ishidden`/`bk_ispaused`/`obj_sort_number`）；**不重建系统属性与表**（避免误删实例数据）；
   - 存在 + `skip` → 跳过；
   - 不存在 → `INSERT cc_ObjDes`（同 §5.2 步骤 3）；若 `--with-system-props`（默认）则写入 Default 分组（§5.2 步骤 4）+ 4 个系统属性（§5.2 步骤 5，标志位以 `bk_switch` 范本为准）+ 默认唯一约束（§5.2 步骤 8，以 `bk_inst_name` 为键）；若 `--with-tables`（默认）则 `CREATE TABLE` 实例分表 + 关联分表（§5.2 步骤 6/7）。
4. **事务**（§5.11.4）：每模型一套写操作（元数据 + 分组 + 系统属性 + 建表）包在同一事务；`--atomic` 下跨模型整体提交，任一模型失败整体回滚（SQLite DDL 事务完全生效；PG/MySQL 退化为逐语句，见 §5.11.4 铁律）。
5. **输出摘要**：新增 N / 覆盖 M / 跳过 K / 失败 F（含分类不存在、模型已存在且 skip）。

**示例**

```bash
# 完整导入：每个模型连带分组/系统属性/实例表/关联表（默认行为）
python3 -m app.cli.cmdb model import \
  --csv ./models.csv --on-duplicate overwrite --atomic

# 仅导入模型元数据（不建表、不注入系统属性），用于补全已有模型的 cc_ObjDes 记录
python3 -m app.cli.cmdb model import \
  --csv ./models.csv --no-with-system-props --no-with-tables --on-duplicate skip
```

---

### 5.11 导入 / 同步 常用规范（通用约定）

本条归纳全部"文件→库"导入命令（`classification import` §5.9、`model import` §5.10、`attribute import` §5.7、`instance import` §5.8）的**通用纪律**。凡是涉及"从外部文件写库"的操作，无论导入分类、模型、属性定义还是实例数据，都应遵循以下规则，以避免脏数据、半成功状态与跨方言陷阱。

#### 5.11.1 文件与编码

| 规范 | 要求 | 理由 / 处理 |
|------|------|-------------|
| 编码 | **统一 `utf-8`**；导入命令默认按 `utf-8` 读，可 `--encoding gbk` 覆盖 | 中文环境 Excel 导出常为非 UTF-8，需显式声明 |
| **BOM 处理** | 自动识别并**剔除 UTF-8 BOM**（首字节 `EF BB BF`） | BOM 会导致表头首列名带不可见字符，引发"列不匹配"误报 |
| 行尾 | 接受 `\n` 与 `\r\n`，解析层统一归一 | Windows 导出常见 `\r\n` |
| 分隔符 | 默认 `,`；支持 `--delimiter '\t'`（TSV） | 字段内含逗号时必须用 TSV 或 RFC 4180 引用转义（见下方"解析器契约"） |
| 空文件 / 空表头 | 表头为空或仅 1 列 → 退出码 `2`，不落库 | 防止"全量误清空" |
| **解析器（强制）** | 生成与读取**必须**走合规 CSV 库（`csv` 模块，`quotechar='"'`，`doublequote=True`，严格 RFC 4180）；**严禁**用 `str.split(',')` 之类的朴素切分 | seed 示例单元格含逗号 JSON（如 `option` / `management_ip`），朴素切分会把单元格劈成多列，导致整批错列、类型全失 |
| **引用 / 转义** | 含逗号、引号或换行符的单元格必须用双引号包裹，内部 `"` 写成 `""`；seed 生成端采用 `QUOTE_ALL` 包裹所有单元格，保证手填编辑后仍可被正确解析 | 用户手填易破坏引号平衡，reader 必须强健；seed 文件即"引用范本" |

> **经验**：所有 CSV 入参先经 `--dry-run` 跑一遍，确认解析行数、列映射、告警数（尤其 `description` 丢弃）后再正式导入。

> **预检门槛（Pre-flight Profile，H1）**：任何非 `--dry-run` 的导入在落库前**必须**先输出一次源画像并经阈值门禁：① 解析行数（数据行总数）、② 检出列清单（表头列名集合）、③ 前 3 行样本预览、④ 预检告警数（未知列 / 必填缺失 / 表头不匹配）。画像失败（0 数据行、表头为空或仅 1 列、表头与允许写入列 0 命中）直接退出码 `2`，**绝不落库**。该画像等同于 ETL 的"Extract 后 Source Profiling"，是上库前的关键闸门。

#### 5.11.2 表头契约（Header Contract）

适用 **instance import**（§5.8 强制）与 **attribute import** 的表头定位（§5.7 以首单元格 `bk_property_id` 行为表头）。

| 规则 | 说明 |
|------|------|
| 表头即契约 | CSV 第 1 行单元格 = 目标表列名（`bk_property_id` 或系统列名）；**导入方不臆造列** |
| 预检先于写入 | 表头逐列比对"允许写入列集"，全部命中才可进入数据行；否则默认报错退出 |
| 未知列策略 | instance：默认报错，`--skip-unknown-columns` 可跳过该列；attribute：D 分组列未知时按 `--group-auto-create` 建分组 |
| 必填列校验 | instance：`bk_inst_name` 一般应在表头内（实例名必填）；attribute：`bk_property_id`/`bk_property_name`/`bk_property_type` 必填且类型合法 |
| 大小写敏感性 | 列名匹配区分大小写（与 `bk_property_id` 约定一致）；建议导出前统一小写 |

#### 5.11.3 枚举 / 列表值归一化

| 类型 | CSV 单元格写法 | 落库形态 | 解析规则 |
|------|----------------|----------|----------|
| `enum` | `running` 或 `运行中`（开 `--enum-by-name`） | option 中的 `id`（`running`） | 按 `id` 精确匹配；`--enum-by-name` 时按 `name` 反查；未命中 → 该行告警/跳过 |
| `enummulti` | `AC,DC` 或多单元格 | JSON 数组字符串 `["AC","DC"]` | 按 `--multivalue-sep`（默认 `,`）拆分，逐个匹配 `id` |
| `list` | `生产环境,测试环境` | JSON 数组字符串 `["生产环境","测试环境"]` | 按分隔符拆分；原 JSON 串则原样存 |
| `bool` | `TRUE/FALSE`、`1/0`、`是/否` | `1/0` | 统一布尔归一；其余值报错 |
| `int`/`float` | `123` / `1.5` | 数值 | 解析失败 → 该行跳过并计入错误清单 |
| `date`/`datetime` | `2026-07-28` / `2026-07-28 11:00:00` | 标准日期/时间串 | 格式不符 → 跳过 |

> **单元格归一（Trim，M2）**：所有单元格在进入类型 / 枚举 / 匹配键解析前**统一 `strip()` 首尾空白**；枚举未命中时先 trim 再去重匹配一次，仍失败才计入拒绝汇（§5.11.6）。匹配键列同样 trim，避免手填 CSV 因首尾空格导致"键看似相等实则不匹配"的静默跳过或重复插入。

> **关键**：复合类型（enum/enummulti/list/array/object）在实例表中一律存 **JSON 字符串**，与 §5.3 类型映射（`TEXT`）保持一致；导出/同步回读时需按 `option` 定义反向解析为显示名。

#### 5.11.4 原子性 vs 非原子性（跨方言）

| 模式 | 行为 | 适用场景 | 跨方言注意 |
|------|------|----------|------------|
| `--atomic`（默认） | 全部 `INSERT/UPDATE` + `ALTER` 包在**单事务**，任一失败整体回滚 | 生产导入、数据一致性优先 | **SQLite 支持 DDL 事务，原子性完全生效**；PostgreSQL/MySQL 的 DDL 会**隐式提交**，`--atomic` 退化为"逐语句尽力提交"，原子性不保证 |
| `--no-atomic` | 逐行提交（非原子模式按 `--batch-size` 分批），失败行仅跳过并记错误清单 | 大文件、脏数据多、允许部分成功 | 中途失败会留下"半导入"状态，需配合唯一键幂等重跑 |

> **铁律**：涉及 `ALTER TABLE`（属性导入加列）时，SQLite 下务必用 `--atomic`；若目标库为 PG/MySQL，应先在迁移脚本中预建列，CLI 仅做数据写入，避免 DDL 自动提交导致的不可回滚。

#### 5.11.5 幂等性与重跑

| 场景 | 幂等手段 | 说明 |
|------|----------|------|
| attribute import | `(bk_obj_id, bk_property_id)` 查重 → `overwrite`/`skip` | 同 id 覆盖、异 id 新增；重跑不重复建列 |
| instance import（无唯一约束） | `--atomic` + 每次先 `--truncate` 或依赖 `generate_id()` 全新增 | 仅历史/手工建的无约束模型会落到此场景 |
| instance import（有唯一约束） | `cc_ObjectUnique` 键 → upsert | 命中 `UPDATE`、未命中 `INSERT`，**天然幂等**，可安全重跑 |
| **批内业务键重复（H2）** | upsert 模式下，先对整批匹配键做集合去重检查 | 同一 CSV 内若两行匹配键相同，后者会**静默覆盖**前者造成批内数据丢失；须侦测并路由到拒绝汇或 `--strict` 终止，计入摘要 `批内重复 D` |
| 推荐默认（已默认生效，C3） | 模型经 CLI 创建时已默认写入 `bk_inst_name` 唯一约束（§5.2 步骤 8） | 实例导入默认可 UPSERT 幂等重跑；如需其它/组合键用 `--unique-by` 或未来 `cmdb unique create` |

#### 5.11.6 错误行隔离与告警

| 规范 | 说明 |
|------|------|
| 单行失败不影响整体 | 默认 `--no-strict`：该行跳过、记错误清单、继续后续行（除非 `--strict` 整体终止） |
| **行级异常全覆盖（含类型转换）** | 所有行级异常（`CliError` / `InvalidIdentifierError` / 数值·布尔转换 `ValueError` / `TypeError`）**均须在行级 `try/except` 捕获并路由拒绝汇**，禁止让 `int()` / `parse_bool()` 等裸异常穿透循环——否则单坏行会使整份 CSV 在本事务内回滚、前面已写入行全部丢失。四类导入（分类 / 模型 / 属性 / 实例）须保持**一致的捕获元组**（已对齐为 `CliError, InvalidIdentifierError, ValueError, TypeError`） |
| 错误清单内容 | 行号 + 列名 + 原因（未知列 / 类型非法 / 唯一冲突 / 枚举未命中 / 必填缺失 / 批内重复键） |
| **拒绝汇（Reject Store，C2）** | 坏行**持久化**到拒绝文件而不仅是内存 / 终端：默认写 `<dir>/<file>.rejects.csv`（无目录则用 `./<file>.rejects.csv`），列为 `原行号,原行内容,失败列,失败原因`；可用 `--reject-out <path>` 覆盖。拒绝汇是 ETL 数据质量闭环的必备，供运营补数后重跑 |
| 批内主键重复（H2） | upsert 模式下先对整批匹配键做去重检查：同一 CSV 内两行匹配键相同 → 后者静默覆盖前者，造成批内数据丢失；侦测到的重复行**路由到拒绝汇**（或 `--strict` 整体终止），计入摘要 `批内重复 D` |
| 摘要输出 | 导入后固定输出：`新增 N / 覆盖 M / 跳过 K / 失败 F / 批内重复 D`（对账后追加 `已装载 L / 期望 E / 一致 ✓或✗`，见 §5.11.11）；`--json` 时结构化输出便于编排 |
| 唯一冲突 | upsert 模式按匹配键覆盖；insert 模式若撞 `(bk_obj_id, bk_inst_id)` 主键 → 计入失败而非崩溃 |

> **全局选项继承**：所有导入命令均接受 §4 的 `--reject-out`（拒绝汇路径）与 `--manifest-out`（运行清单路径，见 §5.11.13）；两者默认即可满足多数场景，无需逐命令重复声明。

#### 5.11.7 空值 / 缺失值处理

| 情况 | 处理 |
|------|------|
| 单元格为空字符串 | 视为 `NULL`（不写该列，或写 `NULL`） |
| 必填列缺失值 | instance：`bk_inst_name` 缺失 → 该行报错/跳过；attribute：`bk_property_id/name/type` 缺失 → 跳过 |
| 系统列缺省 | `bk_obj_id`/`bk_supplier_account` 自动注入；`bk_inst_id` 缺则 `generate_id()`（默认） |
| `option`/`description` 空 | 允许为空；`description` 列不存在时按 §5.7.1 丢弃并告警 |

#### 5.11.8 性能与批量

| 项 | 建议 |
|----|------|
| 批量提交 | 非原子模式按 `--batch-size`（默认 `500`）分批 `executemany`，降低事务开销 |
| 大文件 | 先 `--dry-run` 校验 → 再 `--atomic` 单事务（小中型）/ `--no-atomic --batch-size 1000`（超大型） |
| 索引 | 导入前若实例表已有大量唯一索引，upsert 的 `SELECT` 命中查询应确保走 `cc_ObjectUnique` 对应索引 |
| 超时 | 超大型导入建议在事务外分批，避免长事务锁表（尤其 SQLite 单写锁） |

#### 5.11.9 字段分组解析一致性（attribute import / attribute create 专项）

**两列语义拆分（对齐上游 bk-cmdb）**：`bk_property_group` = 分组 **ID**（`bk_group_id`，语义标识），`bk_group_name` = 分组 **显示名**（`bk_group_name`，用户可读）。二者拆分后，分组归属与显示名不再耦合到同一 CSV 列。

**`resolve_or_create_group(c, oid, grp_id, grp_name, auto_create, name_cache)` 解析顺序**：

| 优先级 | 条件 | 行为 |
|------|------|------|
| 1 | 显式 `grp_id` 且 `cc_PropertyGroup.bk_group_id` 已存在 | 直接返回该 `bk_group_id` |
| 2 | `grp_name` 已命中（已存在或本轮 `name_cache` 已建） | 返回同一 `bk_group_id`（**显示名去重**，镜像上游 `grpNameIDMap`） |
| 3 | `auto_create` 且给了 `grp_name` | `bk_group_id = generate_group_id()`（随机全局唯一串），以该 `grp_name` 命名建组，写入 `name_cache` |
| 4 | `auto_create` 且仅给 `grp_id` | 经 C1 白名单 `validate_identifier(grp_id)` 后以其为 ID 建组，显示名取 `KNOWN_GROUP_NAMES.get(grp_id, grp_id)` |
| 5 | 其它（未命中且不建组） | 回落 `default` |

> `generate_group_id()`（`app.utils.tools`）：20 位 base32 小写随机串（`abcdefghijklmnopqrstuvwxyz234567`），对齐上游 `group.go:NewGroupID(false)` 的 `xid.New()`——**非顺序、不要求小写标识符**，与记录主键 `id`（`generate_id()` 自增）是两回事。

| 规则 | 说明 |
|------|------|
| 显示名去重 | 同一导入批次内，相同 `bk_group_name` 复用同一随机 `bk_group_id`，不会因多行而出现多个同名分组 |
| 缺省分组 | 未显式指定分组时，所有业务属性归入 `default`（与 §1 核心约束一致，**不再强制 base**） |
| 显示名单一来源 | `KNOWN_GROUP_NAMES`（`app.definitions`，原 `default→基础信息 / auto→自动发现信息… / role→角色 / proc_port→监听信息`）为内置 ID→显示名唯一真相源；CLI 与 `migrate.py` 共用，避免漂移 |
| C1 适用范围收窄 | 自动建组生成的随机 `bk_group_id` **不受 C1 白名单约束**；仅当用户显式给出 `bk_property_group` ID 且该 ID 必须新建（规则 4）时才校验 C1 |
| 与 scaffold / API 对齐 | 解析逻辑与 §5.6 `groups`、后端分组 API（POST/PUT/DELETE `/models/<id>/property-groups`）保持一致，避免"同一显示名映射出不同 ID" |

#### 5.11.10 同步（Sync）场景扩展建议

> 当下 CLI 仅覆盖"单向导入"（文件 → 库）。若未来扩展**双向同步**（库 → 文件 / 库 → 库 / 跨环境），建议遵循：

| 同步方向 | 建议机制 |
|----------|----------|
| 库 → 文件（导出） | 复用属性/实例查询接口，导出 CSV 时列序对齐本文导入表头契约，保证"导出的文件可原样回导" |
| 库 → 库（环境迁移） | 以 `bk_inst_id`/`bk_property_id` 为稳定键做 upsert；供应商账户固定 `'0'`，不做多租户搬运 |
| 增量同步 | 依赖 `last_time`/`bk_operate_time` 时间戳做增量游标，避免全量重导 |
| 冲突策略 | 同步默认 `overwrite`（目标端以源端为准）；保留 `--on-duplicate skip` 以保护目标端既有人工数据 |

#### 5.11.11 装载后对账（Reconciliation，H3）

ETL 信任来自"源 − 拒绝 == 目标"。Load 阶段落库后**必须执行一次对账**，否则无法证明装载完整：

| 步骤 | 说明 |
|------|------|
| 期望行数 `E` | `E = 数据总行 − 失败 F − 跳过 K − 批内重复 D`（即本应成功写入的行） |
| 实际装载 `L` | 对目标表执行 `SELECT COUNT(*)`，仅统计本次受影响的模型 / 匹配范围（如 upsert 命中更新的行计入 L；`--truncate` 重载场景以重载后全表计数为准） |
| 一致性断言 | `L == E` 则对账通过（摘要标记 `一致 ✓`）；否则摘要标记 `一致 ✗` 并以退出码 `1` 告警（通用错误，见 §9），提示"源有效行与实际装载不等，可能部分丢失" |
| `--json` 字段 | 摘要对象含 `expected / loaded / reconciled` 三字段，便于编排层断言 |
| apply 跨阶段 | `scaffold apply` 在每个阶段（分类 / 模型 / 属性 / 实例）结束后分别对账，最后一并汇总；任一阶段 `✗` 整体退出码取 `1` |

#### 5.11.12 装载血缘（Lineage，M1）

ETL 可追溯性要求"这批行来自哪次运行"，否则无法按批次回滚或界定增量范围。lite 实例表 schema 固定，故采用**旁路血缘表 + 运行清单**双轨：

| 机制 | 说明 |
|------|------|
| 旁路血缘表 `cc_ImportBatch` | 建议新增轻量元数据表：`(_id TEXT, batch_id TEXT, source_file TEXT, bk_obj_id VARCHAR, loaded_at TIMESTAMP, row_count INTEGER, reject_count INTEGER)`；每次导入（尤其 `instance import` / `scaffold apply`）写入一行，`batch_id` 取 `seed/<ts>` 目录名或 `time.strftime` 时间戳 |
| 行级关联 | 当前实例表无 `batch_id` 列，**不强制**每行打标（避免改 schema）；血缘以"批 → 文件 → 受影响行范围"粒度存在 `cc_ImportBatch`，足以支撑按批次审计与重跑定位 |
| run-manifest 固化 | `batch_id` 同时写入运行清单（§5.11.13），使"批次 ↔ 输入文件 ↔ 参数"可追溯 |
| 增量扩展 | 未来若需行级血缘，可在实例表追加 `bk_batch_id` 列（经 `cc_ObjAttDes` + `ALTER`，复用 §5.3 机制），与 `cc_ImportBatch` 关联 |

#### 5.11.13 运行清单与校验和（Run Manifest，M3）

可重现 ETL 需要可审计的运行档案。每个导入命令成功（或部分成功）结束后**写出运行清单**：

| 项 | 说明 |
|----|------|
| 默认路径 | `--manifest-out <path>`，默认 `./.run.json`（在 `seed/<ts>` 目录内执行时取 `<dir>/.run.json`） |
| 内容 | `{ "command": "...", "input": "<abs-path>", "sha256": "<文件校验和>", "params": {...}, "rows": {...}, "added/updated/skipped/failed/intra_dup": N, "batch_id": "...", "ts": "<ISO8601>" }` |
| 用途 | ① 校验和用于检测"同一文件重复运行"或文件被篡改；② 配合退出码实现"幂等重跑可核对"；③ 审计与排障时还原当时命令行与数据版本 |
| apply 聚合 | `scaffold apply` 将各阶段清单聚合为 `<dir>/.run.json` 一项 `stages[]`，便于整体回看 |

#### 5.11.14 域与跨字段校验（M4）

类型 / 枚举域校验之外，ETL 数据质量还应覆盖"按类型的必填性"与"引用完整性"：

| 校验 | 规则 | 失败处理 |
|------|------|----------|
| 类型 → option 必填 | `bk_property_type ∈ {enum, enummulti, list}` 时，对应 `option` / 数据配置列**必须非空且为合法 JSON**；为空或非法 → 该行计入拒绝汇（§5.11.6） | 拒绝汇 |
| 引用完整性（FK） | `instance import` 的 `--upsert-key` 列、以及表头列，必须真实存在于目标表"允许写入列集"；`model import` 的 `bk_classification_id` 必须已存在于 `cc_ObjClassification` | 预检即报错（退出码 `2` / `3`） |
| **upsert 匹配键存在性** | `instance import` 由 `cc_ObjectUnique` 解析出的匹配列（`bk_property_id`）**必须全部出现在 CSV 表头内**；任一缺失 → 预检报错（退出码 `2`），避免逐行 `WHERE k=:v` 构造时 `KeyError` | 预检即报错（退出码 `2`） |
| 必填列完整性 | `bk_obj_id` / `bk_obj_name` / `bk_classification_id`（模型）、`bk_property_id` / `bk_property_name` / `bk_property_type`（属性）、`bk_inst_name`（实例）缺失 → 拒绝该行 | 拒绝汇 |
| 可扩展钩子 | 预留 `--validate <rule>` 或配置化校验钩子位，未来可加 范围 / 正则 / 跨字段一致性（如 `bk_inst_id` 与 `id` 一致性）校验，不硬编码于主流程 | 拒绝汇 / `--strict` 终止 |

> **设计意图**：上述校验与 §5.11.2 表头契约、§5.11.3 类型归一形成"**预检（表头 / 域）→ 转换（类型 / 枚举）→ 校验（跨字段 / FK）→ 拒绝汇 → 装载 → 对账**"的完整 ETL 数据质量链路。

---

## 6. 数据库操作与指南映射表

| CLI 动作                | 指南章节         | 涉及表                     | 关键字段/约束                                 |
| --------------------- | ------------ | ----------------------- | --------------------------------------- |
| classification create | 2.1          | `cc_ObjClassification`  | `bk_classification_id` UNIQUE           |
| model create（元数据）     | 2.2          | `cc_ObjDes`             | `bk_obj_id` PRIMARY KEY，`bk_ispaused=0` |
| model create（分组）      | 2.3          | `cc_PropertyGroup`      | 仅 `default` 一组（修正：不再强制 base）            |
| model create（系统属性）    | 2.4          | `cc_ObjAttDes`          | 4 个系统属性，`ispre=true`                    |
| model create（实例表）     | 2.7          | `cc_ObjectBase_0_pub_*` | `bk_inst_id` NOT NULL                   |
| model create（关联表）     | 2.8          | `cc_InstAsst_0_pub_*`   | 双向关联分表                                  |
| attribute create（定义）  | 2.4          | `cc_ObjAttDes`          | `(bk_obj_id, bk_property_id)` 复合主键      |
| attribute create（加列）  | 2.7 + 2.4 映射 | `cc_ObjectBase_0_pub_*` | ALTER ADD COLUMN，类型来自 `get_sql_type`    |
| attribute import（CSV） | 2.4 + 2.7 + 2.3 | `cc_ObjAttDes` + `cc_PropertyGroup`(+`cc_ObjectUnique`) + `ALTER cc_ObjectBase_0_pub_*` | 同 `bk_property_id` 覆盖/新增（`--on-duplicate`）；`--atomic` 控制 ALTER 是否单事务；`description` 列 lite 未实现，默认丢弃并告警（不提供补齐开关） |
| classification import（CSV） | 2.1 | `cc_ObjClassification` | 同 `bk_classification_id` 覆盖/跳过；`--atomic` 控制单事务 |
| model import（CSV） | 2.2 + 2.3 + 2.4 + 2.7 + 2.8 | `cc_ObjDes` + `cc_PropertyGroup` + `cc_ObjAttDes` + 两张分表 | 等价于 §5.2 循环；`--with-system-props`/`--with-tables` 控制完整度；覆盖仅更新元数据不重建表 |
| instance import（CSV） | 2.7 + 指南八 `cc_ObjectUnique` | `cc_ObjectBase_0_pub_*` | 表头预检匹配实例表列；无唯一约束→INSERT、有→UPSERT；`--atomic` 控制是否单事务；`--generate-inst-id` 补实例 ID |
| scaffold seed（CSV） | — | 仅生成文件（不落库） | 创建 `seed/<12位时间戳>/` 与示例 CSV（参考 bk_switch + bk_deployment，覆盖 enum/enummulti/list/bool/int/longchar） |
| scaffold apply（CSV） | 2.1 + 2.2 + 2.3 + 2.4 + 2.7 + 2.8 | `cc_ObjClassification` + `cc_ObjDes` + `cc_PropertyGroup` + `cc_ObjAttDes` + 两张分表 | 按依赖顺序执行目录内 CSV，等价于 §5.9/§5.10/§5.7/§5.8 串联；`--atomic` 跨阶段单事务 |
| table create          | 2.7 / 2.8    | 两张分表                    | `IF NOT EXISTS` 幂等                      |

---

## 7. 实现要点（复用现有模块）

| 复用点                                   | 来源                    | 用途                                   |
| ------------------------------------- | --------------------- | ------------------------------------ |
| `query_one` / `query_all` / `execute` | `app.db.executor`     | 所有读写，统一命名参数，防注入                      |
| `get_sql_type(type)`                  | `app.definitions`     | 属性类型→SQL 类型映射（单一真相源，仅认 16 种 Go 合法类型） |
| `SYSTEM_PROPERTIES`                   | `app.migrate.migrate` | 4 个系统属性模板                            |
| `convert_enum_option()`               | `app.migrate.migrate` | 简单数组→标准 enum option                  |
| `generate_id()`                       | `app.utils.tools`     | 分组记录主键（`id` 列）/ 属性 / 关联记录 ID 生成（全局唯一递增） |
| `generate_group_id()`                | `app.utils.tools`     | 分组语义标识 `bk_group_id` 的随机全局唯一串（详见 §5.11.9） |
| `resolve_or_create_group()`          | `app.cli.cmdb`        | 分组"按 ID/显示名查重 → `--group-auto-create` 建组（随机 ID）"统一解析 |
| `KNOWN_GROUP_NAMES`                  | `app.definitions`     | 内置分组 ID→显示名单一真相源（CLI 与 migrate 共用） |
| `settings.DATABASE_URI`               | `app.config.settings` | 默认数据库连接                              |
| `config_by_env`                       | `app.config`          | `--env` 联动多库                         |

**事务**：模型创建与属性创建的多步写操作需包在同一事务内，任一步失败整体回滚（保证"模型存在但缺表/缺属性"的中间态不会出现）。

**ID 生成契约（C2）**：所有写入行的 `_id` / `id` 必须由调用方**逐行独立生成**——`_id = "{bk_obj_id}.{bk_property_id}"`（分组为 `"{bk_obj_id}.{bk_group_id}"`、模型自身为 `bk_obj_id`），`id = generate_id()`；**禁止多行复用同一 `id`**（否则 `cc_ObjAttDes.id` 主键冲突，整事务回滚）。`generate_id()` 与后端 API **共用同一序列**，避免前后端撞号。**作用域说明（F）**：`generate_id()` 产出**全局唯一**递增整数；即便 `migrate.py` 对 `cc_ObjAttDes.id` 采用每模型局部计数器，CLI 的全局 id 也更为严格、不会撞号；若 `cc_ObjAttDes` 以 `(bk_obj_id, id)` 为唯一键，全局 id 仍安全。

**标识符安全（C1，单一强制入口）**：所有拼入 DDL 的标识符（`bk_obj_id` / `bk_property_id` / **显式给定的分组 ID** / CSV 表头列名）**必须**经 `^[a-z][a-z0-9_]*$` 白名单校验、转义内部 `"` 后加双引号包裹；命名参数（`:key`）仅保护 VALUE，**标识符不得直接插值**进表名/列名。**实现要求（D）**：新增 `app.utils.safety.validate_identifier(name) -> bool`（不合法抛 `InvalidIdentifierError`）作为**唯一**校验入口，所有命令在拼 DDL 前统一调用，**禁止在各命令内散落正则**。> ⚠️ C1 适用范围收窄：分组 `bk_group_id` 在 `--group-auto-create` 自动建组时由 `generate_group_id()` 生成（随机串，**不来自用户输入**，故无需也不受 C1 约束）；仅当用户**显式给出** `bk_property_group` ID 且该分组必须新建时，才对该 ID 校验 C1（见 §5.11.9 规则 4）。

---

## 8. 关键流程时序（model create）

```
用户输入: cmdb model create --bk_obj_id X --bk_obj_name 应用系统 --bk_classification_id bk_application
   │
   ├─[1] 校验分类 bk_application 存在? ──否──► 报错退出(非0)
   ├─[2] 校验模型 X 不存在? ──已存在──► 按 --on-duplicate 处理(error 报错退出/skip 跳过/overwrite 覆盖)
   ├─[3] BEGIN TRANSACTION
   │     ├─ INSERT cc_ObjDes
   │     ├─ INSERT cc_PropertyGroup ×1 (default)
   │     ├─ INSERT cc_ObjAttDes ×4 (系统属性)
   │     ├─ CREATE TABLE cc_ObjectBase_0_pub_X
   │     └─ CREATE TABLE cc_InstAsst_0_pub_X
   ├─[4] COMMIT
   └─[5] 输出成功摘要(JSON / 文本)
```

`attribute create` 在步骤 [3] 中额外执行 `INSERT cc_ObjAttDes` + `ALTER TABLE ... ADD COLUMN`。

---

## 9. 错误处理与退出码

| 退出码 | 场景                  |
| --- | ------------------- |
| `0` | 成功                  |
| `1` | 通用错误（SQL 执行失败、约束冲突） |
| `2` | 参数错误（缺必填项、类型非法）     |
| `3` | 依赖缺失（如模型引用的分类不存在）   |
| `4` | 已存在且 `--on-duplicate=error`（默认）   |
| `5` | 数据库不可达 / 连接失败（如 `database is locked`，见 §2 运行约束 C4）       |

所有错误以 `{"error": "...", "step": "..."}` 形式输出到 **stderr**（`--json` 仅提供结构化明细，不改变退出码）；成功结果（摘要 / 查询）输出到 **stdout**。故 `--json` 消费方应**以退出码判定成败**，而非依赖从 stdout 解析错误体。`--dry-run` 成功返回 `0`，预检失败返回 `2`。装载后对账不一致（§5.11.11）以退出码 `1` 告警。

---

## 10. 与 `migrate.py` 的关系

| 对比项     | `migrate.py`                                        | `cmdb` CLI                                |
| ------- | --------------------------------------------------- | ----------------------------------------- |
| 角色      | 全量初始化（首次建库、重建数据）                                    | 增量写操作（开发期随时扩展）                            |
| 幂等      | 全程 `IF NOT EXISTS` + 删库重建                           | 单对象级幂等（`--skip-if-exists` / `--on-duplicate`）    |
| 数据源     | Python 数据列表（`CLASSIFICATIONS` / `BUILTIN_MODELS` 等） | 命令行参数 / scaffold 规格文件                     |
| 实例数据    | 导入 `instances/*.json`                               | 不负责（实例由 API 或手动录入）                        |
| 前端 JSON | 不自动改 `index.json`                                   | 不自动改（`scaffold` 仅生成后端数据，前端定义仍走指南 3.3/3.4） |

> 结论：**两者互补**。CLI 专注"已建库后的局部增量变更"，不改变迁移脚本的权威性。若需把 CLI 创建的模型固化为项目默认，应将其反向回填到 `migrate.py` 的数据列表，再走一次全量迁移验证。

---

## 11. 示例会话

```bash
# 1) 新建分类（如尚无"应用系统"分类）
python3 -m app.cli.cmdb classification create \
  --bk_classification_id bk_application \
  --bk_classification_name 应用系统 \
  --bk_classification_icon icon-cc-application

# 2) 新建模型（自动带分组/系统属性/实例表/关联表）
python3 -m app.cli.cmdb model create \
  --bk_obj_id bk_application_system \
  --bk_obj_name 应用系统 \
  --bk_classification_id bk_application

# 3) 逐个加业务属性（自动 ALTER 实例表加列）
python3 -m app.cli.cmdb attribute create \
  --bk_obj_id bk_application_system --bk_property_id name \
  --bk_property_name 名称 --bk_property_type singlechar --isrequired true

python3 -m app.cli.cmdb attribute create \
  --bk_obj_id bk_application_system_test --bk_property_id status \
  --bk_property_name 状态 --bk_property_type enum \
  --option '[{"id":"running","name":"运行中","type":"text","is_default":true},{"id":"stopped","name":"已停止","type":"text","is_default":false}]'

# 4) 复核
python3 -m app.cli.cmdb model show --bk_obj_id bk_application_system --json

# 5) 或一次性从规格创建
python3 -m app.cli.cmdb scaffold --file ./specs/app_system.json --dry-run   # 先预览
python3 -m app.cli.cmdb scaffold --file ./specs/app_system.json             # 再执行
```

执行后可通过后端 API 验证：

```bash
curl http://localhost:5000/api/v1/models/bk_application_system/attributes
curl -X POST http://localhost:5000/api/v1/models/bk_application_system/instances \
  -H 'Content-Type: application/json' \
  -d '{"data":{"bk_inst_name":"财务系统","name":"财务系统","status":"running"}}'
```

### 11.1 CSV 模式（seed / apply）示例

```bash
# 1) 生成带示例的 seed 目录（12 位时间戳目录名，参考 bk_switch + bk_deployment）
python3 -m app.cli.cmdb scaffold seed --out-dir ./seed
# → ./seed/260729001336/
#     ├─ classifications.csv
#     ├─ models.csv
#     ├─ attributes_bk_switch.csv      # enum/enummulti/list/bool/int/longchar 示范
#     ├─ attributes_bk_deployment.csv  # dep_hosts/dep_ns/type(enum) 示范
#     └─ instances_bk_switch.csv

# 2) 用户编辑上述 CSV（增删行、改值）后，先 dry-run 复核解析与映射
python3 -m app.cli.cmdb scaffold apply --dir ./seed/260729001336 --dry-run

# 3) 正式执行：分类→模型→属性→实例，单事务；同 id/同实例键覆盖
python3 -m app.cli.cmdb scaffold apply --dir ./seed/260729001336 --atomic
```

> 若只需单独导入某类数据，可直接用对应命令读取 seed 目录内的同名文件，例如
> `python3 -m app.cli.cmdb model import --csv ./seed/260729001336/models.csv --atomic`。

---

## 12. 待确认 / 后续扩展

| 项    | 说明                                                                                                |
| ---- | ------------------------------------------------------------------------------------------------- |
| 关联创建 | 指南 2.5/2.6 的 `cc_AsstDes` / `cc_ObjAsst` 暂未纳入 CLI，可作为 `cmdb association create` 后续扩展              |
| 唯一约束 | 模型经 CLI 创建时已默认写入 `bk_inst_name` 唯一约束（§5.2 步骤 8）；后续可扩展 `cmdb unique create` 写组合约束、`--unique-by` 覆盖默认键，并联动后端校验                                     |
| 前端同步 | `scaffold` 当前只写后端；是否反向生成 `index.json` / `attributes/*.json` 待定                                    |
| 方言兼容 | SQLite 用 `ALTER TABLE ADD COLUMN`；PostgreSQL/MySQL 同样支持，但类型名需经 `sqlglot` 转换，CLI 应统一走项目方言层而非手写 DDL |

---

> 本文档为**设计文档，不含实现代码**。下一步可按第 5 节逐命令落地 `app/cli/cmdb.py`（或 `typer` 应用），并复用第 7 节列出的现有模块。
