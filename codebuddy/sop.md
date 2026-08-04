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

## 6. 声明

- 本文档是 **CodeBuddy Sandbox 内的过程记录**，**仅作参考**。
- 所有路径、端口、二进制位置、supervisord 形态、镜像源都**依赖当时环境**，换机器/换集群后务必重新探查再落地。
- 预览 URL 永远通过「发布为应用」机制获取，**不要凭记忆构造域名**。
- 端口托管分工：`:5000` 后端归 supervisord，`:3000` 前端归发布机制，二者不重叠。
