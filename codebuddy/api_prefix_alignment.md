# API 前缀对齐报告

> 方案：**双注册 ＋ 前端迁移**，统一前缀 **`/api/v1`**
> 时间：2026-09-03 20:40 ~ 21:20
> 结论：**121 条路由零冲突，兼容路径 9/9 行为一致，顺带修复 1 个生产环境静默失效的 bug**

## 1. 整改前的混乱状况

后端 14 个 blueprint 中，11 个规范（`url_prefix='/api/v1/xxx'` + route 写相对路径），另外 3 个存在两类问题：

| Blueprint | 原注册方式 | route 内路径 | 问题 |
|---|---|---|---|
| `association_bp` | 无 `url_prefix` | `/find/associationtype` 等 11 个上游风格 + `/api/instances/<id>/associations`、`/api/instances/<id>/related`、`/api/v1/associations/candidates` | **三种风格挤在一个 bp**，前缀硬编码进 route |
| `user_bp` | 无 `url_prefix` | 全部 `/api/usercustom/...`、`/api/users` | 前缀硬编码，且缺 `/v1` 一层 |
| `unique_bp` | 无 `url_prefix` | 全部 `/find/objectunique/...` | 无前缀 |

其中 `/find/associationtype` 这类**是刻意对齐上游 bk-cmdb topo_server 的路径**（源码注释与 `__init__.py` 原第 31 行「旧版 API 路径保持向后兼容」均有说明），因此不能直接改掉，只能在保留的前提下增加规范镜像。

## 2. 后端改动

### 2.1 路由声明去硬编码

| 文件 | 改动 |
|---|---|
| `app/api/v1/association.py` | `/api/v1/associations/candidates` → `/associations/candidates`；**删除 2 个死路由** `/api/instances/<id>/associations`、`/api/instances/<id>/related` |
| `app/api/v1/user.py` | `/api/usercustom/...` → `/usercustom/...`，`/api/users` → `/users`（6 处） |
| `app/api/v1/model.py` | `instance_bp` 的 `/<instance_id>/associations` 补 `obj_id` 查询参数透传 |

**关于删除的 2 个死路由**：它们与 `instance_bp` 的 `/api/v1/instances/<id>/associations`、`/related` 功能重复，且前端一直只调用后者（`association_bp` 版注册出的是 `/api/instances/...`，少一层 `/v1`，从无调用方）。若给整个 bp 加 `/api/v1` 前缀，这两条会与 `instance_bp` 产生**同 URL 双 endpoint 的隐蔽冲突**，故移除。

被删版本独有的 `obj_id` 性能参数（传入时直接定位 `cc_InstAsst_*` 分表，不传则遍历所有分表）已补到 `instance_bp` 的生效实现中，能力不丢。

### 2.2 注册逻辑重构（`app/api/v1/__init__.py`）

前缀统一抽为 `API_V1_PREFIX = '/api/v1'` 常量，只在此文件声明；三个 bp 双注册：

```python
# 兼容路径（deprecated，勿新增调用）
app.register_blueprint(association_bp)                       # /find/associationtype ...
app.register_blueprint(unique_bp)                            # /find/objectunique/...
app.register_blueprint(user_bp, url_prefix='/api')            # /api/usercustom/...

# 规范前缀镜像（迁移目标）
app.register_blueprint(association_bp, url_prefix=API_V1_PREFIX, name='association_v1')
app.register_blueprint(unique_bp,      url_prefix=API_V1_PREFIX, name='unique_v1')
app.register_blueprint(user_bp,        url_prefix=API_V1_PREFIX, name='user_v1')
```

同一 bp 重复注册依赖 Flask >= 2.0.1 的 `name` 参数（当前运行 **2.3.3**）。两次注册**共用同一批视图函数**，因此兼容路径与镜像路径的行为、鉴权、返回体不存在实现漂移；待外部调用方迁移完毕，删除「兼容注册」区块即可收口。

## 3. 前端改动（18 处调用迁移）

按 `topo.js`/`service.js` 的既有写法抽 `API_BASE = '/api/v1'` 常量：

| 文件 | 迁移处数 | 内容 |
|---|---|---|
| `src/api/association.js` | 6 | `/find|create|delete/instassociation`、`/find/associationtype`、`/find/objectassociation` |
| `src/api/instance.js` | 3 | `/find/${objId}` |
| `src/api/user-custom.js` | 5 | `/api/usercustom/...`、`/api/users` |
| `src/api/client.js` | 4 | `/find|create|update|delete/objectunique/...`（该文件其余数十处本就硬编码 `/api/v1`，故保持同风格不引入常量） |

迁移后全局扫描：上游风格调用与旧 `/api/` 前缀调用**均零残留**。

## 4. 顺带修复：生产模式下的静默失效 bug

`cmdb_ui_lite/server.js` 的代理白名单原为 `/api`、`/health`、`/find`、`/create`、`/delete` —— **漏了 `/update`**。

后果：前端旧代码用 `PUT /update/objectunique/object/<id>/unique/<id>` 更新唯一约束，该路径不匹配任何代理规则，被当作前端路由返回 `index.html`，请求**从未到达后端**。dev 模式下由 webpack devServer proxy 覆盖，所以只在生产模式暴露。

本次迁移把前端调用改为 `/api/v1/update/...`（以 `/api` 开头）已绕过该问题；同时补上 `/update` 规则，使**兼容路径的四个动词齐全**，保证声明的「兼容可用」在代理层也成立。

验证（经 3000 端口）：

| 请求 | 响应 | 判定 |
|---|---|---|
| `POST /api/v1/find/associationtype` | 后端 JSON（8 条关联类型） | 代理正常 |
| `PUT /update/objectunique/object/__nonexist__/unique/999999999` | 后端 JSON `keys must be a non-empty list` | **修复生效**（原返回 HTML） |
| `POST /notinwhitelist/foo`（对照组） | 前端 `<!doctype html>` | 白名单机制正常，上一项确因新增规则才通 |

## 5. 验证结果

| 验证项 | 结果 |
|---|---|
| Flask 路由总数 / URL+method 冲突 | **121 条 / 0 冲突** |
| 双注册成对性 | association 12+12、unique 4+4、user 6+6，全部成对 |
| 兼容路径 vs v1 镜像行为一致性 | **9 / 9 一致**（HTTP 状态 + result/code + data 结构指纹） |
| `objectunique` 两路径返回 | **逐字节完全相同** |
| 前端构建 | 通过（11.7s，无报错） |
| 构建产物路径 | `/api/v1` 常量 6 处 + 各路径片段齐全，旧路径零残留 |
| 前端页面 / JS chunk | HTTP 200 |
| CLI `asst-type list` | 8 条，未受影响 |
| `py_compile` | `association.py` / `user.py` / `model.py` / `__init__.py` 全通过 |

关键路径确认可用：`/api/v1/associations/candidates`（前端原调用，靠 v1 镜像继续有效）、`/api/usercustom/...`（靠 `/api` 兼容注册继续有效）。

## 6. 遗留事项

| 事项 | 说明 |
|---|---|
| `AssociationService.get_related_instances`（`association_service.py:755`）成为孤儿方法 | 随死路由删除后已无调用方。它直接查分表，比现行 `InstanceService.get_related_instances`（内部走不传 `obj_id` 的全分表扫描慢路径）更高效，**建议后续用它替换慢实现**，而非直接删除 |
| 兼容注册区块 | 待外部调用方全部迁移到 `/api/v1` 后删除，即可彻底收口 |
| `server.js` 的 `/find /create /update /delete` 四条代理规则 | 仅为兼容路径存在；兼容区块收口后可一并简化为只留 `/api` 与 `/health` |
