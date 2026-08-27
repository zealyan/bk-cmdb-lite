# CMDB-Lite CLI 使用手册

> 适用后端：`cmdb_server_lite`（FastAPI/Flask 单进程，SQLite/MySQL/PostgreSQL 三库通用）
> 入口：`python3 -m app.cli.cmdb <命令组> <子命令> [选项]`
> 框架约束：复用 `app.db` 的连接池/引擎与事务纪律；SQL 经 `adapt_sql` 做方言转译（标识符引号、AUTOINCREMENT→AUTO_INCREMENT/SERIAL、INSERT OR REPLACE→upsert），**同一套命令在三库下行为一致**。
> 多租户：供应商账户固定 `'0'`（单租户，设计文档 §1），命令无需传供应商。

---

## 1. 全局选项

所有子命令均接受以下公共选项（来自父解析器，命令前/后均可）：

| 选项 | 说明 |
|------|------|
| `--db <path>` | SQLite 文件路径（默认走 settings 的 `cmdb_dev.db`，与后端共用同一库） |
| `--env <env>` | 环境：`default`/`development`/`testing`/`production`（默认 `development`） |
| `--dry-run` | 仅打印将执行的 SQL，不落库（DDL/DML 均不提交） |
| `--json` | JSON 结构化输出（便于脚本解析） |
| `--yes`/`-y` | 跳过危险操作的二次确认 |

---

## 2. 命令总览

| 命令组 | 子命令 | 说明 |
|--------|--------|------|
| `classification` | `create` / `import` | 模型分类 |
| `model` | `create` / `import` / `show` / `list` / `delete` | 模型（含系统属性与实例表） |
| `mainline` | `add` / `show` / `remove` / `fix-unique` | **主线关联**（`bk_mainline`，biz-set-module 层级） |
| `association` | `create` / `delete` / `list` | **通用（非主线）模型关联** ← 本次新增 |
| `attribute` | `create` / `import` | 模型属性 |
| `instance` | `import` | 实例导入（CSV） |
| `table` | `create` | 实例表 |
| `user` | `create` | 用户（无 UI） |
| `scaffold` | `spec` / `seed` / `apply` / `from-csv` | 规格驱动建模 |
| `auth` | （子命令见 `auth_cmd.register`） | 鉴权管理 |

> ⚠️ **主线 vs 通用关联的区别**
> - `cmdb mainline` 管理 **`bk_mainline`** 主线关联，用于把模型挂进 biz→set→module→host 拓扑层级链（自动回填 `bk_parent_id`）。
> - `cmdb association` 管理 **普通关联类型**（`default`/`belong`/`run`/`connect` 等），用于"set 关联任意通用模型"这类**非层级**关联。
> - 两者写入同一张 `cc_ObjAsst`，但 `bk_asst_id` 不同；通用接口**禁止**使用 `bk_mainline`，主线接口**只**接受 `bk_mainline`。

---

## 3. 通用模型关联 `association`

### 3.1 约束与幂等

- **关联类型必须存在**：`--asst-id` 须已注册于 `cc_AsstDes`（默认内置 `default`/`belong`/`run`/`connect` 等；自定义类型需先经 migrate 或直写 `cc_AsstDes`）。
- **禁止主线类型**：`--asst-id bk_mainline` 会被显式拦截（"bk_mainline 为主线专用关联类型，通用模型关联不可使用；请用 mainline 接口"）。
- **源/目标模型必须存在**：`--src` / `--dst` 须已存在于 `cc_ObjDes`。
- **幂等主键**：`bk_obj_asst_id` 固定格式 `{src}_{asst_id}_{dst}`，天然唯一。
  - `--on-exist skip`（默认）：已存在则跳过，返回 `existing=true`；
  - `--on-exist update`：已存在则更新 `mapping`/`on_delete`。

### 3.2 `create` —— 创建（幂等）

```bash
cmdb association create \
  --src <源模型ID> \
  --dst <目标模型ID> \
  --asst-id <关联类型ID> \
  [--mapping 1:1|1:n|n:1|n:n] \
  [--on-delete <策略>] \
  [--name <显示名>] \
  [--on-exist skip|update] \
  [--dry-run] [--json]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--src` | ✅ | 源模型 ID（如 `set`） |
| `--dst` | ✅ | 目标模型 ID（如 `bk_slb_server`） |
| `--asst-id` | ✅ | 关联类型 ID（须存在于 `cc_AsstDes` 且非 `bk_mainline`） |
| `--mapping` | ❌ | 关联基数，默认 `1:n` |
| `--on-delete` | ❌ | 删除策略，默认 `none` |
| `--name` | ❌ | 关联显示名；缺省由"源模型名 + 关联类型名 + 目标模型名"拼接 |
| `--on-exist` | ❌ | `skip`（默认，已存在跳过）/ `update`（已存在更新） |

返回字段：`bk_obj_asst_id` / `id` / `created` / `updated` / `existing` / `src` / `dst` / `asst_id`。

### 3.3 `delete` —— 删除（级联清理实例关联）

```bash
cmdb association delete \
  --asst-id-key <bk_obj_asst_id> \        # 方式一：直接给主键（优先）
  [--src <源> --dst <目标> --asst-id <类型>] \   # 方式二：(src,dst,asst-id) 三元组算主键
  [--dry-run] [--json]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--asst-id-key` | 二选一 | 直接给定 `bk_obj_asst_id` 主键 |
| `--src` / `--dst` / `--asst-id` | 二选一 | 三者齐全时计算主键 `src_asstId_dst` |

行为：
- 删除 `cc_ObjAsst` 中的模型关联定义；
- **级联清理**所有模型实例关联分表（`cc_InstAsst_0_pub_{oid}`）中匹配该 `bk_obj_asst_id` 的记录（返回 `inst_deleted` 计数）；
- 若目标为 `bk_mainline`，显式拦截（"bk_mainline 为主线专用关联，不可经通用接口删除；请用 mainline 接口"）；
- 若不存在，返回 `deleted=false, found=false`（不报错）。

### 3.4 `list` —— 列举

```bash
cmdb association list [--src <源模型ID>] [--asst-id <关联类型ID>] [--json]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--src` | ❌ | 按源模型过滤 |
| `--asst-id` | ❌ | 按关联类型过滤 |

返回所列举的 `cc_ObjAsst` 行（含主线与非主线；如需只看通用关联，用 `--asst-id default` 等具体类型过滤）。

### 3.5 完整示例：让"集群(set)"关联"后端服务器(bk_slb_server)"

```bash
# 1) 创建通用关联（幂等，重复执行安全）
cmdb association create --src set --dst bk_slb_server --asst-id default --mapping 1:n
# → 模型关联 已创建: set_default_bk_slb_server

# 2) 再次执行 → 幂等跳过
cmdb association create --src set --dst bk_slb_server --asst-id default
# → 模型关联 已存在跳过: set_default_bk_slb_server

# 3) 列举 set 的所有模型关联（含主线 set_mainline_biz 与本条通用关联）
cmdb association list --src set --json

# 4) 删除（级联清理实例关联）
cmdb association delete --src set --dst bk_slb_server --asst-id default
# → 模型关联已删除: set_default_bk_slb_server（级联清理实例关联 N 条）
```

### 3.6 等价 API 接口（无前缀，旧版兼容路径）

| 方法 & 路径 | 请求体 | 说明 |
|-------------|--------|------|
| `POST /create/objectassociation` | `{bk_obj_id, target_obj_id, bk_asst_id, mapping?, on_delete?, bk_obj_asst_name?, on_exist?}` | 创建（幂等） |
| `POST /delete/objectassociation` | `{bk_obj_asst_id}` 或 `{bk_obj_id, target_obj_id, bk_asst_id}` | 删除（级联） |
| `POST /find/objectassociation` | `{condition: {bk_obj_id?, bk_asst_id?, target_obj_id?}}` | 查询 |

> 字段别名：`bk_obj_id`≡`src_obj_id`，`target_obj_id`≡`bk_asst_obj_id`。返回与 CLI 同构的 `result/data`（`result=true` 表示成功）。

---

## 4. 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 通用错误 / 对账不一致 |
| `2` | 参数错误 / 预检失败（如关联类型不存在、标识符非法） |
| `3` | 依赖缺失（如源/目标模型不存在） |
| `4` | 已存在且 `--on-duplicate error` |
| `5` | 数据库不可达 / locked |

异常（非法标识符、依赖缺失、SQL 失败等）由 `main()` 统一捕获并以 `emit_error` 输出，退出码对应上表。
