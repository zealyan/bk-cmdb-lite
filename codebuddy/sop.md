# bk-cmdb-lite 本地开发 / 预览 SOP

> 适用场景：在 **CodeBuddy Sandbox** 内拉取、改造、部署并预览 `bk-cmdb-lite`（Python Flask 后端 + Vue 2 前端，开发库用 SQLite，无 MongoDB / Redis / ZooKeeper）。
>
> ⚠️ **本文件仅作 CodeBuddy Sandbox 内的参考记录**。各步骤中的路径、端口、二进制位置、supervisord 控制方式均为「当时本机环境」的实测值，**不具备通用性**。换环境时必须以实际探查结果为准，自行调整，切勿照抄。

---

## 0. 总览（简要步骤）

| # | 阶段 | 关键动作 | 产物 |
|---|---|---|---|
| 1 | 拉取代码 | clone 指定分支到 `/workspace/bk-cmdb-lite` | 后端 `cmdb_server_lite` / 前端 `cmdb_ui_lite` / 原项目 `bk-cmdb` |
| 2 | 部署环境 | 装依赖 → 迁移建库 → 前端构建 → 起后端 → 起前端 | 后端 :5000、前端 :3000 |
| 3 | 打开预览页 | 注册 supervisord → `notify` 取 URL | 可访问的预览链接 |

> 第 1–2 步为常规流程，本文**重点在第 3 步**（预览 / `notify` / `supervisor`）。第 2 步部署结果见 `/workspace/deploy_status.md`。

---

## 1. 部署（简要，重点在能跑起来）

> 以下命令均为「参考写法」，实际目录与镜像源按本机情况调整。

| SOP 步骤 | 参考命令（需按实际环境改写） |
|---|---|
| 后端依赖 | `pip install -r cmdb_server_lite/requirements.txt`（国内建议清华/腾讯云镜像） |
| 数据库迁移 | 进入 `cmdb_server_lite` 后 `rm -f cmdb_dev.db && python3 -m app.migrate.migrate` |
| 前端构建 | 进入 `cmdb_ui_lite` 后 `npm install`（npmmirror） + `npm run build`，产出 `dist/` |
| 后端启动 | 进入 `cmdb_server_lite` 后 `python3 run.py`（默认 :5000） |
| 前端预览 | 进入 `cmdb_ui_lite` 后 `node server.js`（默认 :3000，代理 `/api` 等到 :5000） |

健康检查：`GET /api/v1/common/health` 应返回 `{"result":true,"status":"healthy"}`。

---

## 2. 打开预览页（重点）

> 目标：让服务**可被外部访问**，且**在 sandbox 休眠/恢复后自动拉起**。

### 2.1 预览技能（preview）核心约束

- 服务必须 **bind `0.0.0.0`**（不能 localhost / 127.0.0.1）。
- 不能用 dev server（`vite dev` / `webpack-dev-server`），前端走 `build` 后的静态产物 + `node server.js` 生产式预览。
- 必须把服务**注册到 supervisord**，否则 sandbox 休眠后进程丢失、预览失效。
- **预览 URL 只能由 `notify` 生成**，绝对不能自己拼域名（domain 随集群动态变化，拼出来必断）。

### 2.2 supervisord 托管（休眠自恢复）

> ⚠️ 本机实测：supervisord 以 **PID 1** 运行，**没有 `supervisorctl` 二进制**，控制入口是一个 **wrapper**：
> `<实际前缀>/bin/supervisord ctl -c <主配置>`（`ctl` 子命令分发到 supervisorctl）。
> ⚠️ 上文 `<实际前缀>`（本机实测为 `/.PlnPyKFp4CRfFtgC1`，**仅示例、非固定**）需按实际环境定位，切勿写死。定位方式：
> `find / -name supervisord -type f 2>/dev/null`（或读 `IDE_EDITOR_SERVER_DIR` 环境变量后拼 `<IDE_EDITOR_SERVER_DIR>/bin/supervisord`）。
> 该 wrapper **只支持子集命令**：`logtail, pid, reload, restart, shutdown, signal, start, status, stop`，**没有 `reread` / `update`**。
> （不同环境可能完全不同，请先 `ps` / `which` 确认实际控制方式。）

**步骤（参考）：**

1. 写程序配置到 include 目录（主配置 `[include]` 已覆盖该路径）：

   ```ini
   # /usr/local/share/supervisor/preview-3000.conf
   [program:preview-3000]
   command=/root/.nvm/versions/node/v22.13.1/bin/node server.js
   directory=/workspace/bk-cmdb-lite/cmdb_ui_lite
   autostart=true
   autorestart=true
   startsecs=2
   startretries=3
   stopsignal=INT
   stopwaitsecs=10
   stdout_logfile=/tmp/preview-3000.log
   stderr_logfile=/tmp/preview-3000.log
   redirect_stderr=true
   environment=PATH="%(ENV_PATH)s",PORT="3000",BACKEND_URL="http://localhost:5000"

   # /usr/local/share/supervisor/preview-5000.conf
   [program:preview-5000]
   command=python3 run.py
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
   environment=PATH="%(ENV_PATH)s",PORT="5000"
   ```

   > 提示：命令里的 `node` / `python3` 建议用**绝对路径**，避免 supervisord 启动时的 PATH 与你交互 shell 不一致导致找不到解释器。

2. 让 supervisord 重新加载配置（因为 wrapper 没有 `reread`/`update`，用 `reload` 纳入新增的 include 程序）：

   ```bash
   # 先按实际环境定位 supervisord（前缀非固定，本机实测 /.PlnPyKFp4CRfFtgC1 仅示例）
   SUP_BIN="$(find / -name supervisord -type f 2>/dev/null | head -1)"
   SB="$SUP_BIN"
   SC="$(dirname "$SUP_BIN")/../supervisord-conf/supervisord.conf"
   "$SB" ctl -c "$SC" reload          # 输出 Added/Changed Groups 即纳入成功
   "$SB" ctl -c "$SC" start  preview-3000 preview-5000
   "$SB" ctl -c "$SC" status          # 确认 RUNNING
   ```

3. 改代码后热重启：`"$SB" ctl -c "$SC" restart preview-5000`（后端） / `preview-3000`（前端）。

### 2.3 notify 取预览 URL（唯一可信来源）

> 服务 RUNNING 后，调用 `notify` 脚本获取可在浏览器打开的链接。**禁止自行拼接 URL**（domain 含动态 sandbox-id / 区域，拼错即 404）。

```bash
/root/.codebuddy/skills/preview/notify 3000   # 前端预览页
/root/.codebuddy/skills/preview/notify 5000   # 后端 API（直连）
```

输出示例（实际以运行时为准）：

```
[Preview] {"port":"3000","url":"https://webview.e2b.bj3.sandbox.cloudstudio.club/?x-cs-sandbox-id=...&x-cs-sandbox-port=3000"}
```

把 stdout 里的 `url` 原样发给用户即可（`?x-cs-sandbox-port=3000` 后的路径如 `/api/v1/models` 可追加）。

---

## 3. 排错速查（本机实测坑）

| 现象 | 本机原因 | 处理 |
|---|---|---|
| `start preview-xxx` 报 `fail to find process` | 配置写在 supervisord 启动之后，未被 `[include]` 加载 | 用 `reload`（非 `reread`/`update`）重载配置 |
| `Unknown command 'reread'` / `'update'` | 控制入口是 wrapper，不支持这两个子命令 | 改用 `reload` 后再 `start` |
| 前端 `node: not found` | supervisord 的 PATH 与交互 shell 不同（nvm 未加载） | conf 里 `command` 用绝对 node 路径 + `environment=PATH="%(ENV_PATH)s"` |
| `/health` 返回「路径不存在」 | 真实健康路由是 `/api/v1/common/health`，不是 `/health` | 改为打 `/api/v1/common/health` |
| `/api/v3/...` 报路径不存在 | 本仓库后端前缀是 `/api/v1/`，无 v3 | 用 `/api/v1/classifications`、`/api/v1/models` 等 |

---

## 4. 声明

- 本文档是 **CodeBuddy Sandbox 内的过程记录**，**仅作参考**。
- 所有路径、端口、二进制位置、supervisord 形态、镜像源都**依赖当时环境**，换机器/换集群后务必重新探查（`ps` / `which` / `ls` / 读主配置 `[include]`）再落地。
- 预览 URL 永远通过 `notify` 获取，不要凭记忆构造。
