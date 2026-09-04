# bk-cmdb-lite 本地开发 / 预览 SOP

> 适用场景：在 **CodeBuddy Sandbox（WorkBuddy Web 版 / CloudStudio 基础设施）** 内拉取、改造、部署并预览 `bk-cmdb-lite`（Python Flask 后端 + Vue 2 前端，开发库用 SQLite，无 MongoDB / Redis / ZooKeeper）。
>
> ⚠️ **本文件是「本沙箱」的过程记录**，路径 / 端口 / 二进制位置 / supervisord 形态均为**当时本机实测值，不具备通用性**。换环境务必重新探查（`ps` / `which` / `ls` / 读主配置 `[include]`）再落地，切勿照抄。

---

## 0. 总览

| # | 阶段 | 关键动作 | 产物 |
|---|---|---|---|
| 1 | 拉取代码 | clone 指定分支到 `/workspace/bk-cmdb-lite` | 后端 `cmdb_server_lite` / 前端 `cmdb_ui_lite` / 原项目 `bk-cmdb` |
| 2 | 部署环境 | 装依赖 → 迁移建库 → 前端构建 → 起服务 | 后端 :5000、前端 :3000 |
| 3 | 打开预览页 | 「发布为应用」完整发布（接线 + 取 URL） | 可访问的 `shareLink` |

> **重点在第 3 步（预览 / 发布 / supervisord）**。第 2 步部署结果见 `/workspace/deploy_status.md`，运行态见 `/workspace/preview_status.md`。

---

## 1. 本沙箱实测事实（必读，避免踩坑）

| 项 | 实测值 / 结论 |
|---|---|
| 沙箱形态 | WorkBuddy Web 版，底层 CloudStudio；`X_IDE_IS_CLOUDSTUDIO=TRUE` |
| SandboxId | `X_IDE_SPACE_KEY=6f9c4b3d0fcc45eb91529ba357b0f8e7`（即用户报的 SandboxId） |
| 区域 | `X_IDE_SPACE_REGION=sh2`，`X_IDE_PREVIEW_DOMAIN=sh2.sandbox.cloudstudio.club` |
| supervisord | 以 **PID 1** 运行；**没有 `supervisorctl` 二进制** |
| supervisord 控制入口 | **wrapper**：`<IDE_EDITOR_SERVER_DIR>/bin/supervisord ctl -c <主配置>`；本机实测前缀 `/.PlnPyKFp4CRfFtgC1`（**非固定**） |
| wrapper 支持命令 | `logtail, pid, reload, restart, shutdown, signal, start, status, stop`（**无 `reread` / `update`**） |
| 主配置 & include | 主配置 `<前缀>/supervisord-conf/supervisord.conf`；`[include]` 覆盖 `<前缀>_run/supervisord-conf/*.conf` 与 `/usr/local/share/supervisor/*.conf` |
| 预览 URL 机制 | **无 `notify` 脚本**（SOP 旧版写的 `/root/.codebuddy/skills/preview/notify` 不存在）；本环境用 **「发布为应用」技能**（`/root/.codebuddy/skills/发布为应用/`）生成 `shareLink` |
| 发布依赖 | 需环境变量 `AGENTOS_RUNTIME_ID`（本沙箱已具备，形如 `2083416838286417920`） |
| 出网限制 | 沙箱 shell **无法直连** `*.sh2.agentos-app.net`（curl 返回 `HTTP 000`）；`shareLink` 只能从**用户浏览器**经 ingress 访问 |

---

## 2. 部署环境（依赖 → 迁移建库 → 前端构建 → 起服务）

> 以下命令按本机目录；镜像源按实际情况（后端清华/腾讯云，前端 npmmirror）。

### 2.1 后端依赖 & 迁移建库

```bash
cd /workspace/bk-cmdb-lite/cmdb_server_lite

# 后端依赖（如 requirements.txt 未装）
pip install -r requirements.txt            # 国内建议 -i https://mirrors.cloud.tencent.com/pypi/simple

# 数据库迁移（首次或需重置时：清库 → 全量迁移）
rm -f cmdb_dev.db && python3 -m app.migrate.migrate
```

**迁移实测坑（已修复，记录以防回归）：**

- `cc_PropertyGroup` 的 PK 是自增 `id` INTEGER（`_id` 非唯一）。老代码用 `INSERT OR REPLACE`，该语句只按 `id` 匹配 → 当某模型已存在 `default` 行（不同 `id`）时会**生成重复的 `default` 组**（旧 `默认` 行 + 新 `基础信息` 行）。
  - 修复：`migrate_property_groups()` 改为「先查后更新 + 删重复行」；补全插入时**省略 `id` 列**让 SQLite 自赋 `MAX(id)+1`，避免 PK 冲突。
- 完整 `migrate()` 是**一次性初始化**：`migrate_attributes()` 用普通 `INSERT`，非空库会触发 UNIQUE 冲突。**重跑必须 `rm -f cmdb_dev.db` 先清库**。
- 健康路由是 `/api/v1/common/health`（**不是** `/health`）；后端 API 前缀是 `/api/v1/`（**无** `/api/v3`）。
- 启动后端：`python3 run.py`（默认 `:5000`，bind `0.0.0.0`）。

### 2.2 前端构建

```bash
cd /workspace/bk-cmdb-lite/cmdb_ui_lite
npm install --registry=https://registry.npmmirror.com   # 或 pnpm/yarn，依 lock 文件
npm run build                                          # 产出 dist/
```

- 前端是**静态构建产物**（`dist/`），预览走 `node server.js` 生产式托管，**不能用 dev server**（`vite dev` / `webpack-dev-server`）。
- `server.js`：`PORT`（默认 3000）绑 `0.0.0.0`；`BACKEND_URL`（默认 `http://localhost:5000`）代理 `/api` 等到后端。改 `src` 后**必须重新 `npm run build`**，否则服务的是陈旧 `dist/`（曾导致"前端显示旧文案"）。
- `package.json` **无 `start` 脚本**（只有 `dev`/`build`/`serve`/`test`），起服务务必用 `node server.js`，而非 `npm start`。
- 关键文案（上游规则，见 §4）：`default`→`基础信息`、`auto`→`自动发现信息（需要安装agent）`、`role`→`角色`、`proc_port`→`监听信息`。

### 2.3 本地起服务（supervisord 托管）

程序配置写到 `/usr/local/share/supervisor/`（已被主配置 `[include]` 覆盖）：

```ini
# /usr/local/share/supervisor/preview-5000.conf   （后端，始终由 supervisord 托管）
[program:preview-5000]
command=/root/.pyenv/versions/3.11.1/bin/python3.11 run.py
directory=/workspace/bk-cmdb-lite/cmdb_server_lite
autostart=true
autorestart=true
startsecs=3
startretries=3
stopsignal=INT
stopwaitsecs=10
stdout_logfile=/tmp/preview-5000.log
stderr_logfile=/tmp/preview-5000.log
redirect_stderr=true
environment=PATH="/root/.pyenv/versions/3.11.1/bin:%(ENV_PATH)s",PORT="5000"
```

> ⚠️ **`:3000` 前端不要放进 supervisord**（见 §3.3 端口分工）。历史上曾同时由 supervisord `preview-3000` 与「发布为应用」机制争抢 :3000，造成冲突。

控制（wrapper）：

```bash
SUP_BIN="$(find / -name supervisord -type f 2>/dev/null | head -1)"
SC="$(dirname "$SUP_BIN")/../supervisord-conf/supervisord.conf"
"$SUP_BIN" ctl -c "$SC" reload              # 纳入新增 include 程序（无 reread/update，用 reload）
"$SUP_BIN" ctl -c "$SC" start  preview-5000
"$SUP_BIN" ctl -c "$SC" status              # 确认 RUNNING
"$SUP_BIN" ctl -c "$SC" restart preview-5000   # 改后端代码后热重启
```

> 也可用 XML-RPC 助手：`python3.11 /root/.codebuddy/artifact/supervisor_ctl.py <status|start|stop|restart> <name>`。

---

## 2.4 数据库方言配置（SQLite / MySQL / PostgreSQL）

一份代码通过 `CMDB_*` 环境变量切换存储，无需改代码。参数在 `app/config/settings.py` 的 `_resolve_*` 中解析；`run.py` 启动时 `load_dotenv('.env')` 加载 `.env`，但 **`load_dotenv` 默认不覆盖已存在的进程环境变量**（override=False），故 shell `export` 的变量优先于 `.env` 文件。

### 2.4.1 环境变量总览

| 变量 | 含义 | 默认值 / 说明 |
|---|---|---|
| `CMDB_DATABASE_TYPE` | 库类型 | 支持 `sqlite` / `postgresql` / `mysql`；别名：`sqlite3`、`pg`/`postgres`/`pgsql`、`mysql5`/`mysql8`/`mariadb`、`duckdb`（均归一化）。空值用当前 config 的 default |
| `CMDB_DB_NAME` | 库名 / SQLite 文件名 | MySQL/PG=库名；SQLite=文件名（落到 `cmdb_server_lite/<文件名>`）。覆盖各环境默认：dev=`cmdb_dev.db`、test=`cmdb_test.db`、prod=`cmdb` |
| `CMDB_DB_HOST` | 服务端地址 | 默认 `127.0.0.1`（**SQLite 不使用**） |
| `CMDB_DB_PORT` | 端口 | 缺省按类型推导：mysql=3306 / postgresql=5432 / sqlite=0。务必显式设，避免切库后沿用旧端口 |
| `CMDB_DB_USER` | 用户名 | 默认 `cmdb`（**SQLite 不使用**） |
| `CMDB_DB_PASSWORD` | 密码 | 默认 `cmdb`（**SQLite 不使用**） |
| `CMDB_DB_ECHO` | 打印每条 SQL | dev 默认 `true`（日志膨胀）；长驻服务设 `false` |
| `CMDB_DB_POOL_SIZE` / `_MAX_OVERFLOW` / `_POOL_RECYCLE` | 连接池 | 默认 5 / 10 / 3600（仅服务端库） |

### 2.4.2 三种方言的最小配置

**SQLite（默认，单机 / 发布 / 无外部依赖）**

```bash
export CMDB_DATABASE_TYPE=sqlite
export CMDB_DB_NAME=cmdb_dev.db      # 文件落在 cmdb_server_lite/cmdb_dev.db
# 无需 HOST/PORT/USER/PASSWORD
python3 run.py                       # 监听 $PORT（默认 5000）
```

- 首次启动 `init_db` + `ensure_user_custom_supplier_column()` 自动建表/补列；全量初始化见 §2.1（`rm -f cmdb_dev.db && python3 -m app.migrate.migrate`）。
- 跨方言 JSON 兜底：`bk_verify_time` 在 MySQL 下被 pymysql 读为 `timedelta`、PG `bytea` 读为 `memoryview`；`app/__init__.py` 注册的 `CMDBJSONProvider` 统一序列化（datetime 分支 `strftime('%Y-%m-%d %H:%M:%S')` 去 T），业务代码无需为方言改动。

**MySQL（本地开发主库，需 Docker 容器 `cmdb-mysql57`）**

```bash
export CMDB_DATABASE_TYPE=mysql
export CMDB_DB_HOST=127.0.0.1
export CMDB_DB_PORT=3306
export CMDB_DB_NAME=cmdb
export CMDB_DB_USER=cmdb
export CMDB_DB_PASSWORD=cmdb
python3 run.py
```

- 容器休眠后常 `Exited`：发布/预览前先 `docker start cmdb-mysql57`；建议 `docker update --restart unless-stopped cmdb-mysql57` 自愈。
- 前置：库需存在且字符集 `utf8mb4`；表由 `app.migrate.migrate` 全量初始化（非空库重跑须先清库）。

**PostgreSQL（生产默认，多租户 / 高并发）**

```bash
export CMDB_DATABASE_TYPE=postgresql     # 或 pg / postgres / pgsql
export CMDB_DB_HOST=127.0.0.1
export CMDB_DB_PORT=5432
export CMDB_DB_NAME=cmdb
export CMDB_DB_USER=cmdb
export CMDB_DB_PASSWORD=cmdb
python3 run.py
```

- 生产 config 默认即 PG；`CMDB_DATABASE_TYPE` 可覆盖为 mysql/sqlite。驱动 `psycopg2-binary` 已在 `requirements.txt`。

### 2.4.3 切换 / 校验

```bash
# 查看当前生效的库类型与连接参数（调试用）
python3 -c "from app.config.settings import get_config as g; c=g('development'); print(c.DATABASE_TYPE, c.DATABASE_NAME, c.DATABASE_PORT, c.DATABASE_HOST)"
# 后端健康（任何方言通用）
curl -s http://localhost:5000/api/v1/common/health
```

- 类型/端口一致性：切库后若未显式 `CMDB_DB_PORT`，端口按新类型自动重算（见 `_DEFAULT_DB_PORTS`），避免「连 MySQL 却用 5432」静默错连。
- CLI 写库坑：CLI（`app/cli/db.py:init_cli_db`）**不读 `.env`**，只认 `os.environ`；要用 MySQL 须先 `export CMDB_DATABASE_TYPE=mysql CMDB_DB_NAME=cmdb ...` 再跑命令，否则回退 SQLite 导致「服务端读 MySQL、CLI 写 SQLite」不一致。

---

## 2.5 登录 / 鉴权环境变量（最小内置方案，无外部 IAM）

鉴权由 `app/auth/*` 实现，分两层开关：**登录强制**（`SKIP_LOGIN`）与 **RBAC 总闸**（`ENABLE_AUTH`），二者解耦——可只免登录不开 RBAC，也可强制登录但关闭 RBAC（全放行）。

| 变量 | 默认 | 作用 |
|---|---|---|
| `CMDB_SKIP_LOGIN` | `true` | 免登录：`current_user` 回落默认 admin（超管），前端不显示登录页、`/auth/me` 返回 `skipLogin:true`。设 `false` 即开启登录页 + token 强制 |
| `CMDB_ENABLE_AUTH` | `false` | 内置 RBAC（模式 B）总开关：`supplier` 隔离 + 创建者自管 + 管理员全权 + 模型级策略。关闭时全局短路放行（零回归） |
| `CMDB_AUTH_BEARER` | `false` | 是否采信 `Authorization: Bearer` 头。**默认关**：规避 agentos 网关注入/覆盖的平台 token 遮蔽真实登录态（表现为「登录后不跳转」）。仅可信链路（本地直连 / 可信反代）才开 |
| `CMDB_AUTH_TOKEN_QUERY` | `false` | `?lite_bk_token=` 兜底承载开关。默认关（URL 泄露面）；仅无 Cookie / 自定义头客户端用 |
| `CMDB_AUTH_PAYLOAD_ORDER` | `COOKIE,X_LITE_TOKEN` | token 来源解析顺序（first-valid-wins）：`COOKIE` / `X_LITE_TOKEN` / `BEARER` / `QUERY`。需启用 Bearer/Query 时覆盖此值 |
| `SECRET_KEY` / `CMDB_SECRET_KEY` | — | 登录 token 签名密钥。**最高优先**：env > `instance/secret_key` 持久化文件 > dev 回退。多 worker / gunicorn / supervisord 部署务必注入同一值，否则签发与 `/me` 校验跨进程密钥不一致 → 「登录后不跳转」 |
| `CMDB_TOKEN_MAX_AGE` | `3600` | token 有效期（秒） |
| `CMDB_DEFAULT_USER` / `CMDB_DEFAULT_SUPPLIER` | `admin` / `0` | 无身份时回落用户 / 供应商（skipLogin 场景） |
| `CMDB_ADMIN_USER` / `CMDB_ADMIN_PASS` | `admin` / `admin` | 启动时自动创建的初始超管（bk_role=1） |

### 2.5.1 常用组合

| 场景 | 变量 |
|---|---|
| 本地开发 / 演示（免登录直接 admin，发布推荐） | `CMDB_SKIP_LOGIN=true`（其余默认） |
| 强制登录 + 不开 RBAC | `CMDB_SKIP_LOGIN=false CMDB_ENABLE_AUTH=false` |
| 强制登录 + 开启内置 RBAC | `CMDB_SKIP_LOGIN=false CMDB_ENABLE_AUTH=true` |
| 多 worker 生产部署 | 注入 `SECRET_KEY=<稳定值>`（或保证 `instance/secret_key` 文件可写且同源）；按需 `CMDB_ENABLE_AUTH=true` |

> 发布到「发布为应用」云运行时（无 MySQL/Redis）时，前端 `server.js` 代理硬编码 `localhost:5000`，前后端须同运行时；后端用 SQLite（`CMDB_DATABASE_TYPE=sqlite CMDB_DB_NAME=cmdb_dev.db`）并 `CMDB_SKIP_LOGIN=true` 免登录，详见 §3.3 与 `cmdb_web_publish/start.sh`。

### 2.5.2 鉴权排错要点

| 现象 | 原因 | 处理 |
|---|---|---|
| 登录后不跳转首页 | `SECRET_KEY` 跨进程不一致，或 `AUTH_BEARER=true` 被网关注入的平台 token 遮蔽真实 token | 固定 `SECRET_KEY` 注入同一值；保留 `AUTH_BEARER=false` |
| 前端报「未登录或登录已失效」(1302100) | `SKIP_LOGIN=false` 但前端未带有效 token | 演示场景改回 `CMDB_SKIP_LOGIN=true` |
| 普通用户建账号被拒 | `ENABLE_AUTH=true` 下仅超管可建 | 预期 RBAC 行为；用超管账号或关 `ENABLE_AUTH` |

---

## 3. 打开预览页（重点：发布为应用 + 端口接线）

> **目标**：服务可被外部访问，且 sandbox 休眠/恢复后自动拉起。

### 3.1 核心约束

- 服务必须 **bind `0.0.0.0`**（不能 localhost / 127.0.0.1）。
- 前端走 `build` 静态产物 + `node server.js`，**不用 dev server**。
- 预览 URL **只能由「发布为应用」机制生成**，**绝对不能自己拼域名**（domain 随集群动态变化，拼出来必断 / 跳 `?reason=unauthorized`）。

### 3.2 「发布为应用」机制（本环境 notify 的等价物）

技能目录：`/root/.codebuddy/skills/发布为应用/`，核心 `scripts/publish.js` + `scripts/lib.js`。它做两件事：

1. **接线（关键）**：POST `http://127.0.0.1:65310/replaceCloudStudioConfig`，把端口注册成"应用"并自启（`restart:true`）——这一步把端口真正接给 ingress 转发。
2. **取域名**：POST agentos `/v2/agentos/artifact-releases`，返回稳定 `shareLink`（基于 `appName` 的 friendly domain，形如 `https://a<md5>.sh2.agentos-app.net`）。

> ⚠️ **必须走完整发布流程**。只做第 2 步（仅注册域名、不接线）会导致"域名解析正常但连不上" → 用户侧报 **"工作空间无法连接"**。这是实测踩过的最大坑。

### 3.3 完整发布流程（正确做法）

```bash
# 0) 前提：:3000 不能被 supervisord 占（避免端口冲突）
#    若之前有 preview-3000：停掉 → 删 /usr/local/share/supervisor/preview-3000.conf → reload
SUP_BIN="$(find / -name supervisord -type f 2>/dev/null | head -1)"
SC="$(dirname "$SUP_BIN")/../supervisord-conf/supervisord.conf"
"$SUP_BIN" ctl -c "$SC" stop    preview-3000
rm -f /usr/local/share/supervisor/preview-3000.conf
"$SUP_BIN" ctl -c "$SC" reload

# 1) 完整发布（接线 + 域名），输出 shareLink
node /root/.codebuddy/skills/发布为应用/scripts/publish.js \
  --dir /workspace/bk-cmdb-lite/cmdb_ui_lite \
  --port 3000 \
  --start-cmd "node server.js" \
  --install-cmd ""
# 输出：{"shareLink":"https://a....sh2.agentos-app.net","verified":true}
```

要点：

- 务必带 `--start-cmd "node server.js"`（`package.json` 无 `start` 脚本）；`--install-cmd ""` 跳过重复 `npm install`（依赖已装时）。
- `verified:true` 表示发布机制已在 :3000 拉起 `node server.js` 且就绪探针通过。
- `shareLink` 基于 `appName`（= `runtimeId` 的 md5），**幂等稳定**：重复发布得到同一链接，用户书签不会失效。

### 3.4 端口托管分工 & 休眠自恢复

| 端口 | 服务 | 托管方 | 说明 |
|---|---|---|---|
| 5000 | 后端 Flask (`run.py`) | **supervisord** `preview-5000` | `autorestart=true`，休眠自恢复 |
| 3000 | 前端 node (`server.js`) | **「发布为应用」机制** (`replaceCloudStudioConfig`, `restart:true`) | 发布时接线并暴露，休眠自恢复 |

两者均能在 sandbox 休眠/恢复后自动拉起；**不要让 supervisord 与发布机制同时托管 :3000**。

### 3.5 本地验证（沙箱 shell 内）

```bash
curl -s -m 5 -o /dev/null -w "前端 :3000 HTTP %{http_code}\n" http://localhost:3000/
curl -s -m 5 http://localhost:5000/api/v1/common/health          # 期望 healthy
curl -s -m 5 http://localhost:3000/api/v1/models/host/property-groups   # 应含 基础信息
```

> 注：后端 Flask 的 JSON 把中文做 **unicode 转义**（`\u57fa\u7840\u4fe1\u606f`=基础信息），`grep 基础信息` 匹配不到 API 返回；要验证请 `grep` 转义串或看 `dist/` 字面量。沙箱 shell 也**无法直连** `*.sh2.agentos-app.net`（`HTTP 000`），`shareLink` 只能从用户浏览器验证。

---

## 4. 上游分组规则（Task C 改造点，便于回看）

bk-cmdb 上游规则在本 lite 版落地为：

- `default` 组（group_id 小写）显示名 = **基础信息**，`bk_group_index = -1`，`bk_isdefault = 1`。
- 合并：`base` → `default`、`agent` → `auto`（lite 旧发明的 `base`/`agent` 已废弃）。
- `auto` 组 = **自动发现信息（需要安装agent）**，`index = 3`（host 模型专属）。
- 其余补充组：`role`→`角色`(2)、`proc_port`→`监听信息`(2)。
- 现状核验：8 个模型（biz / bk_slb* / bk_switch / host / module / set）均含唯一 `default`(基础信息, -1)；仅 `host` 额外含 `auto`；无 `base`/`agent`/名为"默认"的残留分组。

---

## 5. 排错速查（本机实测坑）

| 现象 | 本机原因 | 处理 |
|---|---|---|
| 用户侧"工作空间无法连接" / TraceId 失败 | 只注册了域名（`createArtifactRelease`），**未接线**（`replaceCloudStudioConfig`）→ ingress 无转发目标 | 走 §3.3 **完整发布流程**（含 setAutoStart） |
| `start preview-xxx` 报 `fail to find process` | 配置写在 supervisord 启动之后，未被 `[include]` 加载 | 用 `reload`（非 `reread`/`update`）重载 |
| `Unknown command 'reread'` / `'update'` | 控制入口是 wrapper，不支持这两子命令 | 改用 `reload` 后再 `start` |
| 前端 `node: not found` | supervisord 的 PATH 与交互 shell 不同（nvm 未加载） | conf `command` 用**绝对 node 路径** + `environment=PATH="%(ENV_PATH)s"` |
| 自拼域名跳 `?reason=unauthorized` | domain 随集群动态变化，手拼必错 | 永远用「发布为应用」生成的 `shareLink` |
| 前端显示旧文案（如仍是"默认"） | 改了 `src` 但没重 `npm run build`，服务的是陈旧 `dist/` | 重 build 后重启 :3000 进程 |
| `/health` 返回「路径不存在」 | 真实路由是 `/api/v1/common/health` | 改打该路径 |
| `/api/v3/...` 报路径不存在 | 本仓库前缀是 `/api/v1/`，无 v3 | 用 `/api/v1/classifications`、`/api/v1/models` 等 |
| `grep 基础信息` 在 API 返回里无匹配 | Flask JSON 把中文 unicode 转义（`\uXXXX`） | grep 转义串，或直接看 `dist/` 字面量 / 用 `jq` |

---

## 6. 服务分类（ServiceCategory）复刻

业务拓扑「服务分类」管理的完整实现（前端模板 + 后端 CRUD），对齐蓝鲸 CMDB 的 `ServiceCategory`（两级树：`bk_parent_id=0` 一级，其余二级；`bk_root_id` 指向一级）。

### 6.1 后端（Flask，SQLite/MySQL/PG 通用）

| 项 | 内容 |
|---|---|
| 表 | `cc_ServiceCategory`（id / bk_biz_id / name / bk_root_id / bk_parent_id / bk_supplier_account / is_built_in） |
| 建表 | `app/service/service_category_service.py: init_service_category_table()`，在 `create_app` 中幂等调用 |
| 路由前缀 | `/api/v1/service/category` |
| DDL | `app/sql/service_category/create_table.sql`（PostgreSQL 方言，运行时转译） |

**接口（均为 BaseResp 格式，result+data）**

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/v1/service/category?bk_biz_id=&bk_supplier_account=` | 列表（扁平 `{info,count}`，前端组装树） |
| POST | `/api/v1/service/category` | 创建，body `{bk_biz_id, name, bk_parent_id?}`（bk_parent_id 缺省=一级） |
| PUT | `/api/v1/service/category/<id>` | 重命名，body `{name}` |
| DELETE | `/api/v1/service/category/<id>` | 删除（**有子分类则禁止**，须先清空二级；`is_built_in=1` 不可删） |

**约束**：同级同名唯一（不区分大小写）；二级下不能再建子级（仅两级）；`is_built_in=1` 不可改名/删除。
**错误码**：`CCErrServiceCategoryHasChildNode=1199020`（一级下存在二级，禁止删除）、`CCErrServiceCategoryBuiltInForbidden=1199021`（内置分类禁止改名/删除）。
**SQL（多方言，PG 方言经 `adapt_sql` 转译）**：`select_list.sql` / `select_one.sql` / `count_name_exists.sql`（同级同名）/ `count_children.sql`（是否有子分类）。

**权限（auth 复刻）**：`app/auth/resource.py` 资源 `SERVICE_CATEGORY = "serviceCategory"`；`app/auth/parser.py` 按 `^/api/v1/service/category(?:/(\d+))?$` 解析 —— GET→FIND（放行读）；POST 取 body `bk_biz_id` 作 CREATE 的 `business_id`；PUT/DELETE 由 `cc_ServiceCategory.bk_biz_id` 反查 `business_id`，实现「按业务隔离」的写操作复核。

### 6.2 前端（Vue，bk-magic-vue）

| 项 | 文件 |
|---|---|
| API 封装 | `src/api/service.js`（`serviceAPI.getServiceCategories / createServiceCategory / updateServiceCategory / deleteServiceCategory`） |
| 视图 | `src/views/service-category/index.vue`（两级树 + 内联编辑 + 删除确认 `$bkInfo`） |
| 内联输入组件 | `src/views/service-category/children/category-input.vue`（挂载自动聚焦） |
| 路由 | `src/router/index.js` → `/business/:bizId/service-category` |
| 菜单 | `src/dictionary/menu.js` + `menu-symbol.js`（`MENU_BUSINESS_SERVICE_CATEGORY`） |

> 数据流向：视图 `getCategories()` → `serviceAPI.getServiceCategories(bizId)` → 后端扁平列表 → `assembleTree()` 按 `bk_parent_id/bk_root_id` 组装两级树。新建/改名/删除后统一 `resetEditState()` + 重新拉取。

### 6.3 模块创建接入服务分类（新建模块弹框）

业务拓扑「新建模块」弹框的「所属服务分类」两级选择器，数据来自 `/api/v1/service/category`，选中二级分类 `id` 作为模块的 `service_category_id` 落库。**对齐上游 `scene_server/topo_server/logics/inst/module.go: CreateModule`**（经 `checkServiceTemplateParam` 校验后 `data.Set(BKServiceCategoryIDField, serviceCategoryID)`）。

| 项 | 内容 |
|---|---|
| 落库列 | `cc_ModuleBase.service_category_id`（INTEGER，DEFAULT 0） |
| 模型属性 | `module` 模型注册 `service_category_id`（bk_property_type=int），使 `InstanceService.create_instance` 的 `valid_fields` 收纳该列 |
| 迁移 | `app/migrate/migrate.py`：① DDL 为新库自带列；② `ensure_module_service_category_column()` 为存量库 `ALTER TABLE cc_ModuleBase ADD COLUMN service_category_id`（步骤 7.3，幂等）；③ `migrate_builtin_model_attributes()` 写入属性目录 |
| 校验/存储 | `topo_service.resolve_module_service_category(biz_id, supplier, raw_sc_id)` 接入 `create_mainline_instance`（model_id=='module' 分支）：存在性（`cc_ServiceCategory` 同租户）+ 业务隔离（`bk_biz_id==0` 全局内置任意业务可用，否则须等于模块业务，否则 `CCErrCommParamsInvalid`）+ 未传则回退内置默认分类（无则落 0） |
| 读取 | 模块列表 `get_module_list_with_statistics`（已 `SELECT *`）与详情 `get_node_detail` 均返回 `service_category_id` |
| 路由 | 前端走 `POST /api/v1/topo/instance/mainline`（`attrs.service_category_id` 透传）；专用 `POST /topo/set/<id>/module` 当前未消费 `attrs`，后续接入需补 `attrs` 透传 |
| 前端 | `src/views/business-topology/children/create-module.vue`：`created()` 调 `serviceAPI.getServiceCategories(bizId)` → 按 `bk_parent_id==0` 分组两级 → 默认选中首个一级及其首个二级；提交 `service_category_id = 选中的二级 id`；`handleCreateModuleSubmit`（`topology-tree.vue`）封装进 `attrs` |

## 7. 排错速查（补充）

| 现象 | 本机原因 | 处理 |
|---|---|---|
| 前端 `ChunkLoadError` / `CSS_CHUNK_LOAD_FAILED`（某 `xxx.HASH.css`） | 发布目录 `cmdb_web_publish/cmdb_ui_lite/dist` 与源码 `dist` 不同步（旧 build 的 entry 引用了已被新 build 覆盖的懒加载 chunk）；浏览器缓存旧 `index.html` 指向已不存在的 hash | 重 `npm run build` → `rm -rf cmdb_web_publish/cmdb_ui_lite/dist && cp -r cmdb_ui_lite/dist cmdb_web_publish/cmdb_ui_lite/dist`；node server.js 读盘且 `no-cache`，无需重启进程。用户侧硬刷新（Ctrl/Cmd+Shift+R）清旧 `index.html` 缓存 |
| 后端 `/api/v1/service/category` 返回「路径不存在」 | 改了后端代码但 supervisord 托管的 `run.py`（:5000）仍是旧进程 | `kill <run.py pid>`，supervisord `autorestart=true` 会自动按新代码拉起（~2s） |

---

## 8. 声明

- 本文档是 **CodeBuddy Sandbox 内的过程记录**，**仅作参考**。
- 所有路径、端口、二进制位置、supervisord 形态、镜像源都**依赖当时环境**，换机器/换集群后务必重新探查再落地。
- 预览 URL 永远通过「发布为应用」机制获取，**不要凭记忆构造域名**。
- 端口托管分工：`:5000` 后端归 supervisord，`:3000` 前端归发布机制，二者不重叠。
