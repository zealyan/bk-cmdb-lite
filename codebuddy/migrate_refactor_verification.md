# migrate 整改验证报告

> 验证对象：`app/migrate/migrate.py` + `app/db/dialect.py` + `app/sql/migrate/*.sql` + `app/migrate/seeds.py`
> 验证时间：2026-09-03 20:00 ~ 20:10
> 结论：**整改通过，零数据回归**

## 1. 整改目标与达成情况

| 规范要求 | 达成状态 | 证据 |
|---|---|---|
| 执行层统一走 `app/db/executor.py` | 通过 | `migrate.py` 全文无 `get_connection()` / `sqlalchemy.text(` / `adapt_sql(` 调用，仅注释提及 |
| 固定 SQL 外置到 `app/sql/migrate/` | 通过 | 6 个文件全部被引用，无孤儿文件（见 §2） |
| 禁止硬编码 SQLite 专有 `INSERT OR REPLACE` | 通过 | HEAD 版 **20 处** → 整改版 **0 处**（仅注释/docstring 保留说明） |
| 种子数据与执行逻辑解耦 | 通过 | 抽离至 `app/migrate/seeds.py` |
| 幂等写入统一走方言层 `upsert()` | 通过 | 22 处 `upsert_sql()` / `upsert()` 调用点 |

代码体量：`migrate.py` 净减 **213 行**（+642 / −855），`dialect.py` +107 行。

## 2. 外置 SQL 文件引用核对

| 文件 | 引用次数 | 用途 |
|---|---|---|
| `select_all_model_ids.sql` | 5 | `SELECT bk_obj_id FROM cc_ObjDes` |
| `insert_property_group.sql` | 2 | 属性分组补全（按模型 / 按属性反推） |
| `update_property_group.sql` | 1 | 属性分组元数据原位刷新 |
| `select_max_attribute_id.sql` | 2 | `MAX(id) FROM cc_ObjAttDes` |
| `select_attribute_id.sql` | 1 | 按 (bk_obj_id, bk_property_id) 查 id |
| `insert_service_category.sql` | 2 | 内置服务分类一级/二级 Default |

**无孤儿文件，无失效引用。** 注释 ASCII 冒号扫描（`grep -P '^\s*--.*:'`）结果为空 —— 上一轮踩到的「注释冒号被 SQLAlchemy `text()` 误识别为 bindparam」隐患已彻底清除。

## 3. 三方言 upsert 生成正确性

以 `cc_ObjAttDes`（复合键）与 `cc_ApplicationBase`（单键）为样本，patch `get_config()` 切方言实测：

| 方言 | 生成语句形态 | 复合冲突键处理 |
|---|---|---|
| sqlite | `INSERT OR REPLACE INTO "t" (...)` | 依赖表唯一约束，无需显式列 |
| mysql | `INSERT INTO \`t\` (...) ON DUPLICATE KEY UPDATE \`c\`=VALUES(\`c\`)` | 反引号 + 依赖唯一键 |
| postgres | `INSERT INTO "t" (...) ON CONFLICT ("bk_obj_id", "bk_property_id") DO UPDATE SET "c"=EXCLUDED."c"` | **复合列正确展开** |

## 4. 空库全量对照（HEAD 原始版 vs 整改版）

方法：临时用 `git show HEAD:` 版本覆盖 `migrate.py` + `dialect.py`，各自在全新空库跑 `DatabaseMigrator().migrate()`，比对全表行数。

**24 / 28 张表行数完全一致。** 4 处差异全部归因于上一轮功能任务，与本轮 SQL 落地整改无关：

| 表 | HEAD | 整改版 | 差异内容 | 归因 |
|---|---|---|---|---|
| `cc_AsstDes` | 6 | 7 | direction `forward` → `src_to_dest`（值域对齐）；新增 `bk_mainline`（主线） | Task #30 关联类型方向整改 |
| `cc_ObjClassification` | 3 | 4 | 新增 `bk_biz_topo`（业务拓扑） | Task #30 主线拓扑关联种子化 |
| `cc_ObjAttDes` | 178 | 180 | 新增 `module.bk_module_type`、`module.service_category_id` | Task #25 服务分类功能 |
| `cc_ServiceCategory` | 表不存在 | 2 | 内置 Default(150901) / Default(150902, parent=150901) | Task #25 建表 + 本轮外置 SQL 落地验证 |

行数一致的表覆盖了本轮 upsert 改造的全部重点对象：`cc_HostBase`=21、`cc_ObjectUnique`=9、`cc_PropertyGroup`=9、`cc_SetBase`=9、`cc_ModuleBase`=20、`cc_ObjAsst`=5、5 张 `cc_InstAsst_*` 分表、4 张 `cc_ObjectBase_*` 实例分表。

## 5. 现有库幂等复跑

复制 `cmdb_dev.db` 后重跑 `migrate()`：**35 / 35 张表行数完全不变**。

```
cc_ObjAttDes=194, cc_ObjDes=10, cc_ObjClassification=4, cc_AsstDes=8, cc_ObjAsst=9,
cc_ObjectUnique=11, cc_PropertyGroup=11, cc_ServiceCategory=13, cc_ApplicationBase=5,
cc_SetBase=12, cc_ModuleBase=28, cc_HostBase=21, cc_ModuleHostConfig=21, cc_UserBase=1, ...
```

## 6. 运行时不回归（API / CLI）

| 入口 | 结果 |
|---|---|
| CLI `asst-type list` | 8 条，direction 显示 `src_to_dest(源到目标)` / `none(无方向)` 正确 |
| `POST /find/associationtype` | `result=true, code=0`，8 条，字段完整 |
| `GET /api/v1/service/category?bk_biz_id=2` | `code=0`，`count=12`，内置 Default 层级正确 |
| `GET /api/v1/service/category`（缺参） | 正确返回 `1199006 缺少业务ID参数`（参数校验未失效） |

`py_compile` 对 `migrate.py` / `seeds.py` / `dialect.py` / `executor.py` 全部通过。

## 7. 待清理的遗留文件（未跟踪，建议手动确认后删除）

| 路径 | 说明 |
|---|---|
| `cmdb_server_lite/cmdb` | 误产生的 11 页 SQLite 库（疑似某次 `CMDB_DB_NAME=cmdb` 误设），非可执行脚本 |
| `cmdb_server_lite/cmdb_dev.db.bak.140949` | 历史备份 |
