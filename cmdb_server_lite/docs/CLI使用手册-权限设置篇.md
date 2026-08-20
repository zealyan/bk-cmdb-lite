# CMDB-Lite CLI 使用手册 · 权限设置篇（auth）

> 配套文档：
> - `CLI使用手册.md`（通用 CLI 约定、全局选项、退出码总表、测试矩阵）
> - `权限配置使用手册.md`（面向 DB / SQL 直接操作；本篇的 CLI 是其等价的命令行封装）
>
> 本篇覆盖命令组 `cmdb auth ...`，底层复用 `app/db/auth.py` 公共数据层（多方言 + 项目 db 框架），与后端 API（`/api/v1/auth/manage`）共用同一套 SQL / 方言逻辑，是 RBAC 的「单一真相源」。

---

## 一、运行环境与前置

| 项 | 说明 |
| --- | --- |
| 调用方式 | 在项目根目录 `cmdb_server_lite/` 执行：`python3.11 -m app.cli.cmdb auth <子命令> [全局选项] [子选项]` |
| 依赖数据层 | `app/db/auth.py`（用户委托 `app/db/user.py`，策略落 `cc_AuthPolicy`） |
| 目标库 | SQLite 默认 `cmdb_dev.db`；可用 `--db` 指向副本（推荐，见 §七 运维注意） |
| 供应商账户 supplier | 默认 `0`（lite 单租户）；多租户时 `--supplier` 须与用户 `bk_supplier_account` 一致 |

### 1.1 RBAC 速览（先理解再动手）

- **默认拒绝、策略允许**：`cc_AuthPolicy` 仅存 `effect='allow'`，无 `deny`；未命中策略即拒绝。
- **`find`（查看）永远放行**：读接口不鉴权，因此「写场景」不含 `find`；`readonly` 场景显式含 `find` 仅用于表达「仅可查看」语义。
- **资源类型 `res_type`**：默认 `modelInstance`；拓扑用 `biz_topology`、主机转移用 `hostInstance`（见 §4.10 `res-type list` 全部取值）。`obj_id` 为模型 ID 或拓扑固定字面量，**省略即类级（`NULL` = 全部模型/全部业务）**，类级策略对「该模型 + 全部模型」均生效（继承语义）。**拓扑/转移类资源另有 `--biz-id` 业务级维度**：省略=全部业务（类级，`business_id=NULL`）；指定 `N`=仅业务 `N`（`business_id='N'`），与类级互不覆盖、互不幂等跳过；判定时 `business_id = 请求业务 OR business_id IS NULL` 即放行（详见 §7.3）。
- **策略幂等**：重复授予同 `(supplier, principal, res_type, obj_id, action)` 会「跳过」而非报错。
- **供应商隔离**：`supplier` 须等于目标用户的 `bk_supplier_account`，否则策略不会被该用户的请求命中（见 §七 多租户）。

---

## 二、全局选项

所有 `auth` 子命令均可前置/后置使用（来自 `cmdb.py` 的 common 父解析器）：

| 选项 | 说明 |
| --- | --- |
| `--db PATH` | SQLite 文件路径；省略则用配置中的 `cmdb_dev.db`。CLI 通过覆写所选环境的 `DATABASE_NAME` 实现，与后端 API 共用同一连接池。 |
| `--env ENV` | 环境：`default` / `development` / `testing` / `production`（默认 `development`）。 |
| `--dry-run` | **不落库**，输出将执行的操作概要（human 文本；`--json` 时输出计划字典）。注意：auth 子命令打印的是「操作计划」，不是原始 SQL 文本。 |
| `--json` | 以 JSON 输出结果（成功结果与错误均输出 JSON）。 |
| `--yes` / `-y` | 跳过危险操作二次确认（auth 子命令均为显式 `--user` 定向，暂无强制二次确认，保留兼容）。 |

> 成功结果输出到 **stdout**；错误输出到 **stderr**。脚本判定成败请依赖**退出码**。

---

## 三、退出码

`auth` 子命令沿用 `app/cli/errors.py` 的统一退出码（详见 `CLI使用手册.md` §1.2）。auth 实际触发：

| 码 | 含义 | auth 典型触发 |
| --- | --- | --- |
| `0` | 成功 | 正常完成；批量授权存在「跳过」仍返回 0 |
| `1` | 通用错误 / 未预期错误 | DB 执行失败、约束冲突等非参数类异常 |
| `2` | 参数错误 | 用户名/动作非法、未知场景、`model-owner` 缺 `--model/--models`、密码 < 6 位、角色非 1/2 |
| `4` | 已存在 | `auth user create` 用户名重复 |
| `5` | 数据库被锁定 | `database is locked`（后端占用连接时，见 §七） |

> 实现注记：`CliError` 与退出码常量已抽离到独立模块 `app/cli/errors.py`。早期版本将其定义在 `cmdb.py` 内，因 `python -m app.cli.cmdb` 会把模块当作 `__main__` 再加载一份，导致 `auth_cmd` 从真实名导入的 `CliError` 与主入口的不是同一个类，`main()` 的 `except CliError` 无法匹配，所有结构化错误被通用分支吞掉（恒返回 `1`）。抽到叶子模块后该问题消除，参数/已存在错误现正确返回 `2` / `4`。

---

## 四、命令参考

### 4.1 `auth user create` — 创建用户

```
cmdb auth user create --name <用户名> --password <明文密码> [--role 1|2] [--supplier 0]
```

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--name` | 是 | — | 用户名（`bk_user_name`，唯一；非空） |
| `--password` | 是 | — | 明文密码，经 werkzeug 哈希后存储；**长度至少 6 位** |
| `--role` | 否 | `2` | `1`=超级管理员，`2`=普通用户 |
| `--supplier` | 否 | `0` | 供应商账户（须与后续策略 supplier 一致） |

示例：
```bash
python3.11 -m app.cli.cmdb auth user create --name kate --password 'Pass@123456' --role 2
# 预期：退出 0，输出 “用户 kate 创建成功（bk_role=2）”
```
错误：
- 用户名重复 → 退出 `4`，stderr：`[ERROR] (4) 用户已存在: kate  step=create_user`
- 密码 < 6 位 → 退出 `2`，stderr：`[ERROR] (2) 密码长度至少 6 位  step=create_user`

---

### 4.2 `auth user list` — 列出全部用户

```
cmdb auth user list
```
示例（含内置 `admin`）：
```bash
python3.11 -m app.cli.cmdb auth user list
# 预期：退出 0，逐行输出
#   admin   role=1  supplier=0
#   kate    role=2  supplier=0
```
> 输出不含密码字段（`bk_password` 已被剥离）。

---

### 4.3 `auth user update` — 修改用户密码

仅更新 `bk_password`（明文经 werkzeug 哈希后存储），不改角色 / 供应商。复用 `app/db/user.py` 的 `update_user_password`，与 `create` 共用同一套哈希与方言逻辑（单一真相源）。

```bash
cmdb auth user update --name <用户名> --password <新明文密码> [--supplier 0]
```
| 参数 | 必填 | 说明 |
|---|---|---|
| `--name` | 是 | 用户名（bk_user_name），必须已存在 |
| `--password` | 是 | 新密码明文（werkzeug 哈希后存储）；**允许任意非空密码**（包括弱密码，区别于 `create` 的 ≥6 位新建防护） |
| `--supplier` | 否 | 供应商账户（默认 `settings.DEFAULT_SUPPLIER=0`）；需与用户 `bk_supplier_account` 一致 |

示例：
```bash
python3.11 -m app.cli.cmdb auth user update --name tom --password tom
# 预期：退出 0，输出
#   用户 tom 密码已更新（bk_role=2）
```
> 设计说明：`update` 不强制密码复杂度（信任管理员显式改密），`create` 仍要求 ≥6 位（防误建弱口令）。若需统一复杂度，可在 `cmd_auth_user_update` 加 `len(args.password) < 6` 校验，与 `create` 对齐。

---

### 4.4 `auth policy grant` — 授予策略（可多动作）

```
cmdb auth policy grant --user <用户名> --action <动作[,动作]> [--model <obj_id>] [--res-type <资源类型>] [--biz-id <业务ID>] [--supplier 0]
```

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--user` | 是 | — | 用户名（principal）；**用户须已存在** |
| `--action` | 是 | — | 动作，逗号分隔：`create` / `update` / `delete` / `find` / `transfer` |
| `--model` | 否 | 类级 | `obj_id`：模型实例=模型 ID；拓扑省略即全部业务（或填 `biz_topology`）；主机转移填 `host` 或省略。**省略则类级 = 全部模型（NULL）** |
| `--res-type` | 否 | `modelInstance` | 资源类型：`modelInstance` / `hostInstance` / `business` / `biz_topology` / `model`（见 §4.10） |
| `--biz-id` | 否 | 全部业务 | 业务级作用域（`biz_topology`/`hostInstance` 专用）：省略→`business_id=NULL` 类级（覆盖全部业务）；指定值（如 `2`）→`business_id='2'` 仅该业务生效。与类级是两条独立策略 |
| `--supplier` | 否 | `0` | 供应商账户 |

示例（按模型授权两动作）：
```bash
python3.11 -m app.cli.cmdb auth policy grant --user kate --action create,update --model bk_switch
# 预期：退出 0，输出 “已为 kate 在 bk_switch 授权 ['create', 'update']：新增 2 / 跳过 0”
```
示例（类级授权，作用于全部模型）：
```bash
python3.11 -m app.cli.cmdb auth policy grant --user kate --action delete
# 预期：退出 0，输出 “已为 kate 在 全部模型(NULL) 授权 ['delete']：新增 1 / 跳过 0”
```
示例（拓扑管理员：集群/模块 可增改删，全部业务类级）：
```bash
python3.11 -m app.cli.cmdb auth policy grant --user kate --res-type biz_topology --action create,update,delete
# 预期：退出 0，“已为 kate 在 全部模型(NULL)（biz=ALL）授权 ['create', 'update', 'delete']：新增 3 / 跳过 0”
```
示例（拓扑管理员·仅业务 2，per-biz 业务级策略）：
```bash
python3.11 -m app.cli.cmdb auth policy grant --user kate --res-type biz_topology --action create,update,delete --biz-id 2
# 预期：退出 0，“已为 kate 在 全部模型(NULL)（biz=2）授权 ['create', 'update', 'delete']：新增 3 / 跳过 0”
# 注：biz=2 与上面的「全部业务」是两条独立行；kate 对业务 2 有权、对业务 1 仍被拒（除非另有类级策略）
```
示例（主机转移权限）：
```bash
# 全部业务（类级）：kate 可把主机转移到任意业务的模块
python3.11 -m app.cli.cmdb auth policy grant --user kate --res-type hostInstance --action transfer
# 预期：退出 0，“已为 kate 在 全部模型(NULL)（biz=ALL）授权 ['transfer']：新增 1 / 跳过 0”

# 仅业务 2（业务级）：kate 仅能把主机转移到业务 2 的模块；转移到业务 1 被拒 1302102
python3.11 -m app.cli.cmdb auth policy grant --user kate --res-type hostInstance --action transfer --biz-id 2
# 预期：退出 0，“已为 kate 在 全部模型(NULL)（biz=2）授权 ['transfer']：新增 1 / 跳过 0”
#   注：请求时业务作用域由目标 module_id 反查 cc_ModuleBase.bk_biz_id 得到（对齐上游 host transfer 的 Parents=[business]）
```
> 幂等：重复授予同条件 → `跳过` 计数 +1，不报错；`新增`/`跳过` 在输出中区分。

---

### 4.5 `auth policy revoke` — 撤销策略

```
cmdb auth policy revoke --user <用户名> --action <动作[,动作]> [--model <obj_id>] [--res-type <资源类型>] [--biz-id <业务ID>] [--supplier 0]
```

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--user` | 是 | — | 用户名（principal） |
| `--action` | 是 | — | 动作，逗号分隔：`create` / `update` / `delete` / `find` / `transfer` |
| `--model` | 否 | 类级 | `obj_id`：模型实例=模型 ID；拓扑填 `biz_topology`；主机转移填 `host`。**省略则撤销该类级（全部模型）及该动作下所有模型级策略** |
| `--res-type` | 否 | `modelInstance` | 资源类型（见 §4.10）；须与授权时一致才能命中 |
| `--biz-id` | 否 | 全部业务 | 业务级作用域：**省略→撤销该动作下全部业务的策略（含类级 NULL 与指定业务）**；指定值→仅撤销该业务的策略 |
| `--supplier` | 否 | `0` | 供应商账户 |

示例（按模型撤销单动作）：
```bash
python3.11 -m app.cli.cmdb auth policy revoke --user kate --action create --model bk_switch
# 预期：退出 0，输出 “已撤销 kate 在 bk_switch 的 create 权限（1 条）”
```
示例（类级撤销，删掉该用户在该动作下的全部模型策略）：
```bash
python3.11 -m app.cli.cmdb auth policy revoke --user kate --action delete
# 预期：退出 0，输出 “已撤销 kate 在 全部模型(NULL) 的 delete 权限（N 条）”
```
示例（撤销拓扑全部写动作，含全部业务）：
```bash
python3.11 -m app.cli.cmdb auth policy revoke --user kate --res-type biz_topology --action create,update,delete
# 预期：退出 0，“已撤销 kate 在 全部模型(NULL)（biz_topology）的 ['create', 'update', 'delete'] 权限（共 3 条）”
```
示例（仅撤销业务 2 的拓扑写动作，保留类级/其它业务）：
```bash
python3.11 -m app.cli.cmdb auth policy revoke --user kate --res-type biz_topology --action create,update,delete --biz-id 2
# 预期：退出 0，“已撤销 kate 在 全部模型(NULL)（biz=2）（biz_topology）的 ['create', 'update', 'delete'] 权限（共 3 条）”
```

---

### 4.6 `auth policy list` — 列出策略

```
cmdb auth policy list [--user <用户名>] [--model <模型ID>] [--action <动作>] [--biz-id <业务ID>] [--supplier 0]
```
所有过滤项均可选；不传则返回全部策略。

示例：
```bash
python3.11 -m app.cli.cmdb auth policy list --user kate
# 预期：退出 0，逐行输出（obj / biz 为 NULL 时显示 ALL）
#   #24   kate   modelInstance   obj=bk_switch   biz=ALL   update   allow

# 仅列出业务 2 的拓扑策略
python3.11 -m app.cli.cmdb auth policy list --user kate --res-type biz_topology --biz-id 2
# 预期：退出 0，逐行输出
#   #30   kate   biz_topology   obj=biz_topology   biz=2   create   allow
#   #31   kate   biz_topology   obj=biz_topology   biz=2   update   allow
#   #32   kate   biz_topology   obj=biz_topology   biz=2   delete   allow
```
列含义：`#<id>  <principal>  <res_type>  obj=<obj|ALL>  biz=<业务ID|ALL>  <action>  <effect>`。

---

### 4.7 `auth policy grant-scenario` — 按场景批量授权

```
cmdb auth policy grant-scenario --user <用户名> --scenario <场景> \
    [--models <模型ID,模型ID>] [--model <模型ID>] [--biz-id <业务ID>] [--supplier 0]
```

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--user` | 是 | — | 目标用户名（principal） |
| `--scenario` | 是 | — | 场景名：`readonly` / `readwrite` / `update-only` / `model-owner` / `topo-admin` / `host-transfer` |
| `--models` | 否 | — | 显式模型 ID 列表（逗号分隔），**覆盖模型场景作用域**（见下表展开规则） |
| `--model` | 否 | — | 单模型 ID；`model-owner` 场景必填（或与 `--models` 二选一） |
| `--biz-id` | 否 | 全部业务 | 业务级作用域（`topo-admin`/`host-transfer` 场景的 biz 维度）：省略→全部业务（类级）；指定 `N`→仅业务 `N`。拓扑/转移忽略 `--model`/`--models` |
| `--supplier` | 否 | `0` | 供应商账户 |

#### 内置场景与展开规则

| 场景 | actions | res_type | 作用域 scope | 不传 `--models` 时 | 传 `--models a,b` 时 |
| --- | --- | --- | --- | --- | --- |
| `readonly` | `find` | modelInstance | all | 1 条（类级） | 1 条（逐模型仍 1 动作） |
| `readwrite` | `create,update,delete` | modelInstance | all | 3 条（类级） | 每模型 3 条 → 共 6 条 |
| `update-only` | `update` | modelInstance | all | 1 条（类级） | 1 条 |
| `model-owner` | `create,update,delete` | modelInstance | model | **需 `--model` 或 `--models`**；单模型 3 条 / 两模型 6 条 | 每模型 3 条 |
| `topo-admin` | `create,update,delete` | **biz_topology** | topo | 3 条（`obj_id` 固定 `biz_topology`）；`--biz-id` 省略=全部业务，指定 `N`=仅业务 `N` | 忽略 `--models`（拓扑不按模型展开） |
| `host-transfer` | `transfer` | **hostInstance** | host | 1 条（`obj_id` 固定 `host`）；`--biz-id` 同上 | 忽略 `--models` |

> 展开语义（`resolve_scenario`，与解析器产出的 `obj_id` 严格对齐）：
> - scope=`all`：无 `--models` → 类级（`obj_id=NULL`）；有 `--models` → 逐模型展开。
> - scope=`model`：必须给 `--model` 或 `--models`，按给定模型逐个展开 3 个写动作。
> - scope=`topo` / `host`：`obj_id` 固定；`--biz-id` 透传为 `business_id`——省略=全部业务（类级），指定 `N`=仅业务 `N`。**忽略 `--model`/`--models`**。

示例：
```bash
# 类级全写（3 条，作用于全部模型）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario readwrite
# 预期：退出 0，“场景[readwrite] 为 kate 批量授权完成：新增 3 / 跳过 0 / 失败 0”

# 单模型 owner（3 条）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario model-owner --model bk_x
# 预期：退出 0，“场景[model-owner] 为 kate 批量授权完成：新增 3 / 跳过 0 / 失败 0”

# （新增）拓扑管理员：集群/模块 可增改删（3 条，全部业务类级）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario topo-admin
# 预期：退出 0，“场景[topo-admin] 为 kate 批量授权完成：新增 3 / 跳过 0 / 失败 0”

# 拓扑管理员·仅业务 2（business_id='2'，与「全部业务」场景互不覆盖）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario topo-admin --biz-id 2
# 预期：退出 0，“场景[topo-admin] 为 kate 批量授权完成：新增 3 / 跳过 0 / 失败 0”

# （新增）主机转移：transfer（1 条，全部业务类级）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario host-transfer
# 预期：退出 0，“场景[host-transfer] 为 kate 批量授权完成：新增 1 / 跳过 0 / 失败 0”

# 主机转移·仅业务 2（business_id='2'，仅业务 2 的模块可转移主机；与「全部业务」互不覆盖）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user kate --scenario host-transfer --biz-id 2
# 预期：退出 0，“场景[host-transfer] 为 kate 批量授权完成：新增 1 / 跳过 0 / 失败 0”
```
错误：
- `model-owner` 未给 `--model/--models` → 退出 `2`，stderr：`[ERROR] (2) 场景 model-owner 需要 --model 或 --models  step=grant_scenario`
- 未知场景 → 退出 `2`，stderr：`[ERROR] (2) 未知场景: xxx（可用: ['readonly', 'readwrite', 'update-only', 'model-owner', 'topo-admin', 'host-transfer']）  step=grant_scenario`

### 4.8 `auth action list` — 列出全部合法 action（只读辅助）

列出 RBAC 白名单 `VALID_ACTIONS`（`create / update / delete / find`）。**不查库**，纯常量输出，用于对照 `--action` 可填值。

```bash
cmdb auth action list [--json]
```

输出（human 直接是逗号分隔一行，可整体复制）：
```bash
python3.11 -m app.cli.cmdb auth action list
# 预期：退出 0，输出 "create,update,delete,find"
```

### 4.9 `auth model list` — 列出全部模型 ID（只读辅助）

列出 `cc_ObjDes` 中**全部**模型的 `bk_obj_id`（按 ID 升序，含已暂停模型）。走与后端一致的多方言 SQL 框架；human 输出为逗号分隔一行，可直接复制进 `--models`。

```bash
cmdb auth model list [--json]
```

输出：
```bash
python3.11 -m app.cli.cmdb auth model list
# 预期：退出 0，例如 "biz,bk_slb,bk_slb_listener,bk_slb_server,bk_switch,host,module,set"
```

> 与 `cmdb model list`（表格形式，含 bk_obj_name / 分类 / 暂停标记）互为补充：本命令专为「喂给 `--models` 参数」优化为单行逗号分隔。

---

### 4.10 `auth res-type list` — 列出全部合法 res_type（只读辅助）

列出 RBAC 资源类型白名单（含说明与每个类型当前可用动作）。**不查库**，纯常量输出，用于对照 `--res-type` 可填值，以及确认某类型是否被网关实际拦截。

```bash
cmdb auth res-type list [--json]
```

输出（human 为「类型 \t 可用动作 \t 说明」逐行）：
```bash
python3.11 -m app.cli.cmdb auth res-type list
# 预期：退出 0，逐行输出
#   modelInstance   create,update,delete,find   模型实例：create/update/delete/find（业务拓扑外的模型 CRUD，受网关拦截）
#   hostInstance    transfer                      主机实例：transfer=主机转移（与主机 update 解耦，受网关拦截）
#   business        -                             业务（reserved：当前路由未暴露业务级写，网关暂不拦截）
#   biz_topology    create,update,delete          集群/模块/主线实例：create/update/delete（上游 IAM 统一映射，受网关拦截）
#   model           -                             模型（reserved：模型元数据管理，解析器未产出该类型，网关暂不拦截）
```

> `business` / `model` 标注 reserved：lite 当前路由未暴露其写端点，解析器不产出这两类资源，
> 故分配给它们的策略不会被任何请求命中（写库无害、只是不生效）。新增资源的授权请优先用
> `modelInstance` / `biz_topology` / `hostInstance`。

---

## 五、实战示例：为 bob 按场景批量授权多模型

目标：让普通用户 `bob` 成为 `bk_x`、`bk_y` 两个模型的「模型负责人」（可新增/编辑/删除，不可越模型）。

```bash
# 0) 准备：确保用户存在（已存在则跳过，退出 0）
python3.11 -m app.cli.cmdb auth user create --name bob --password 'Bob@123456' --role 2

# 1) 按场景批量授权（model-owner + 多模型）
python3.11 -m app.cli.cmdb auth policy grant-scenario --user bob --scenario model-owner --models bk_x,bk_y
# 预期：新增 6 / 跳过 0 / 失败 0

# 2) 校验：列出 bob 的策略
python3.11 -m app.cli.cmdb auth policy list --user bob
# 预期：6 行，obj 分别为 bk_x / bk_y，action 为 create/update/delete

# 3) 回收（如需）：类级撤销 bob 的全部 delete
python3.11 -m app.cli.cmdb auth policy revoke --user bob --action delete
```

> 行为预期（与 API 一致）：bob 对 `bk_x`/`bk_y` 可增删改；对其它模型默认拒绝；`find` 查看始终放行。

---

## 六、`--json` 输出参考

| 命令 | JSON 关键字段 |
| --- | --- |
| `auth user list` | `{"count": N, "users": [...], "human": "..."}` |
| `auth policy list` | `{"count": N, "policies": [{"id","supplier","principal","res_type","obj_id","business_id","action","effect"}, ...], "human": "..."}` |
| `auth policy grant` | `{"principal","obj_id","business_id","actions", "granted", "skipped", "human": "..."}`（`obj_id`/`business_id` 为 `null` 表示类级） |
| `auth policy grant-scenario` | `{"scenario","principal","items", "granted","skipped","failed", "human": "..."}` |
| `auth action list` | `{"count": 5, "actions": ["create","update","delete","find","transfer"], "csv": "...", "res_types": [...], "human": "..."}` |
| `auth res-type list` | `{"count": 5, "res_types": [{"res_type","description","valid_actions"}, ...], "csv": "...", "human": "..."}` |
| `auth model list` | `{"count": N, "model_ids": [...], "csv": "...", "human": "..."}` |
| `auth user create` | 用户字段（`bk_password` 已剥离）+ `human` |
| `auth user update` | 用户字段（`bk_password` 已剥离）+ `human`（密码已重算哈希） |

示例：
```bash
python3.11 -m app.cli.cmdb auth policy list --user kate --json
# {"count": 1, "policies": [{"id": 24, "supplier": "0", "principal": "kate",
#   "res_type": "modelInstance", "obj_id": "bk_switch", "action": "update", "effect": "allow"}],
#  "human": "..."}
```

---

## 七、运维注意

### 7.1 SQLite 锁（重要）

后端（`run.py`）使用 SQLAlchemy **`StaticPool`** 持有常连同一 `cmdb_dev.db`。CLI 写同一 SQLite 文件时若后端仍在占用，会触发 `database is locked`（退出 `5`）。

- **写类命令**（`user create` / `policy grant` / `revoke` / `grant-scenario`）建议**先停止后端进程**再执行；或：
- 跑前拷贝一份沙箱库，全程加 `--db /tmp/cli_auth.db`，避免污染开发库、也避开锁：
  ```bash
  cp cmdb_dev.db /tmp/cli_auth.db
  python3.11 -m app.cli.cmdb auth policy grant-scenario --user bob --scenario model-owner \
      --models bk_x,bk_y --db /tmp/cli_auth.db
  ```
- `--dry-run` 不落库，可随时运行，用于预演。

### 7.2 多租户 supplier

lite 默认 `supplier=0`（单租户）。若启用多租户（如 `id0`/`id1` 隔离）：
- 创建用户时的 `--supplier` 必须与该用户 `bk_supplier_account` 一致；
- 授权 / 撤销 / 列表的 `--supplier` 也须一致，否则策略不会被该用户的请求命中（查询按 `supplier` 过滤）。

### 7.3 类级 / 模型级 / 业务级

- **模型级 vs 类级（`--model`）**：
  - 省略 `--model` → `obj_id=NULL` 类级策略，对**全部模型**生效（含未来新建模型）。
  - 指定 `--model` → 仅对该模型生效。二者可并存；撤销时 `--model` 省略即回收该类级及该动作下所有模型级策略。
- **业务级（`--biz-id`，`biz_topology`/`hostInstance` 专用）**：
  - 省略 `--biz-id` → `business_id=NULL` 类级策略，**覆盖全部业务**（旧的「业务无关」行为默认保留，单条策略对所有业务生效）。
  - 指定 `--biz-id N` → `business_id='N'` 业务级策略，**仅对业务 N** 的集群/模块/转移生效。
  - 二者是**两条互相独立**的策略行：`policy_exists` 按「`(business_id='N')` 与 `business_id=NULL` 互为不同」严格判定，故授予类级不会幂等跳过已授的 `--biz-id 2`，反之亦然。
  - **判定规则**（`policy_query_allow`）：请求解析出的 `business_id` 命中 `business_id=<本业务>` **或** `business_id IS NULL`（类级）即放行。因此「类级策略」是全部业务的超集——持有类级授权的用户对所有业务都有权；而「`--biz-id 2`」的用户仅对业务 2 有权、对业务 1 仍被拒（除非另有类级或业务 1 的策略）。
  - 解析器如何得到 `business_id`：创建集群取自路由 `<bizId>`；创建模块 / 编辑 / 删除节点由 `set`/`module` 的 `instId` 反查 `cc_SetBase`/`cc_ModuleBase` 的 `bk_biz_id`。

---

## 八、常见错误速查

| 现象（stderr） | 退出码 | 原因 / 处理 |
| --- | --- | --- |
| `[ERROR] (4) 用户已存在: <name>` | 4 | 用户名重复；换名或仅做授权 |
| `[ERROR] (2) 密码长度至少 6 位` | 2 | 密码过短 |
| `[ERROR] (2) 非法角色: <r>` | 2 | `--role` 仅 `1`/`2` |
| `[ERROR] (2) 用户不存在: <name>` | 2 | `update` 目标用户不存在；先 `auth user create` |
| `[ERROR] (2) 新密码不能为空（--password 必填）` | 2 | `update` 的 `--password` 为空字符串 |
| `[ERROR] (2) 非法动作: [...]（仅 ...）` | 2 | `--action` 含非 `create/update/delete/find/transfer` 的值 |
| `[ERROR] (2) 非法资源类型: <r>（仅 ...）` | 2 | `--res-type` 非 `modelInstance/hostInstance/business/biz_topology/model`（`grant`/`revoke` 亦受 argparse `choices` 拦截） |
| `[ERROR] (2) 未知场景: <s>` | 2 | 场景名拼错，限 `readonly/readwrite/update-only/model-owner/topo-admin/host-transfer` |
| `[ERROR] (2) 场景 model-owner 需要 --model 或 --models` | 2 | `model-owner` 必须指定模型 |
| `[ERROR] (5) 数据库被锁定 ... database is locked` | 5 | 后端占用连接；停后端或改用 `--db` 副本 |

---

## 九、与后端 API 的关系

`auth` CLI 与后端蓝图 `app/api/v1/auth_manage.py` 共用 `app/db/auth.py` 公共数据层，语义完全一致：

| CLI | 等价 API |
| --- | --- |
| `auth user create/list` | `POST/GET /api/v1/auth/manage/users` |
| `auth user update` | 无对应 API（仅 CLI）；后端改密走 `POST /api/v1/auth/manage/users` 的运维路径 |
| `auth policy grant/revoke/list` | `POST/DELETE/GET /api/v1/auth/manage/policies` |
| `auth policy grant-scenario` | `POST /api/v1/auth/manage/policies/batch`（带 `scenario`） |
| `auth action list` / `auth model list` / `auth res-type list` | 无对应 API；CLI 专属只读辅助查询（列出合法 action / 全部模型 ID / 全部资源类型） |

> API 侧受 `ENABLE_AUTH` 总开关与 `_require_admin()`（开启时要求 `bk_role=1`）约束；CLI 侧直接操作库、不走 HTTP，也无 admin 校验——适合运维 / 初始化场景。若需 SQL 直操，参见 `权限配置使用手册.md`。
