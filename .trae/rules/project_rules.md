# CMDB 项目开发规范

## 项目变量定义

```bash
# 项目根目录（所有子项目的父目录）
export PROJECT_ROOT=/workspace

# 项目子目录
BK_CMDB=$PROJECT_ROOT/bk-cmdb          # 原项目（蓝鲸 CMDB 源码）
CMDB_UI_LITE=$PROJECT_ROOT/cmdb_ui_lite  # 前端子项目
CMDB_SERVER_LITE=$PROJECT_ROOT/cmdb_server_lite # 后端子项目
```

---

## 一、项目架构

```
$PROJECT_ROOT/                          # 项目根目录
├── bk-cmdb/              # 原项目（蓝鲸 CMDB 源码）
│   ├── src/             # 源代码
│   │   ├── common/      # 公共模块
│   │   └── ui/          # 原项目 UI
├── cmdb_ui_lite/         # 前端子项目 (Vue 2 + bk-magic-vue + Vue CLI)
└── cmdb_server_lite/    # 后端子项目 (Python 3.11 ~ 3.14 + Flask 2.3.3 + SQLAlchemy)
```

---

## 二、项目概述

### 前端项目 (cmdb_ui_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Vue 2.7.0 + bk-magic-vue 2.5.9-beta.39 + Vue Router 3.0.1 + Vuex 3.0.1 + Axios 1.6.8 |
| 构建工具 | Vue CLI 5.x (@vue/cli-service ~5.0.0) |
| 端口 | 3000 (预览 + API 代理)、8080 (Vue CLI dev server) |
| E2E 测试 | Playwright 1.59.1 |

### 后端项目 (cmdb_server_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Python 3.11 ~ 3.14 + Flask 2.3.3 + SQLAlchemy >=2.0.35 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) / MySQL (可选) / DuckDB (兼容) |
| 方言处理 | sqlglot 19.8.0 |
| 端口 | 5000 |
| API 前缀 | `/api/v1`（主要）、无前缀（旧版兼容路由 `/find`、`/create`、`/delete`）、`/api`（用户自定义配置） |
| 健康检查 | `http://localhost:5000/api/v1/common/health` |

---

## 三、技术栈详情

### 3.1 后端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Python** | Python | 3.11 ~ 3.14（可选范围，已移除 `.python-version` 硬编码） | Python 版本 |
| **Web 框架** | Flask | 2.3.3 | 轻量级 Web 框架 |
| **数据库连接池** | SQLAlchemy | >=2.0.35 | 仅使用连接池与原生 SQL 执行，**禁用 ORM Model** |
| **方言转换** | sqlglot | 19.8.0 | 多数据库 SQL 方言处理 |
| **环境变量** | python-dotenv | 1.0.0 | `.env` 文件加载 |
| **日志** | coloredlogs | 15.0.1 | 彩色日志输出 |
| **PostgreSQL 驱动** | psycopg2-binary | 2.9.7 | PostgreSQL 数据库驱动 |
| **MySQL 驱动** | pymysql | 1.1.0 | MySQL 数据库驱动 |
| **SQLite** | 标准库 | 3.14+ | Python 内置 sqlite3 模块 |
| **CORS** | Flask-Cors | 4.0.0 | 跨域支持 |
| **单元测试** | pytest | 7.4.2 | Python 单元测试框架 |
| **Flask 测试** | pytest-flask | 1.2.0 | Flask 测试插件 |

### 3.2 前端技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| **框架** | Vue | 2.7.0 |
| **UI 库** | bk-magic-vue | 2.5.9-beta.39 |
| **路由** | Vue Router | 3.0.1 |
| **状态管理** | Vuex | 3.0.1 |
| **HTTP 客户端** | Axios | 1.6.8 |
| **构建工具** | @vue/cli-service | ~5.0.0 |
| **E2E 测试** | Playwright | 1.59.1 |
| **样式** | Sass/SCSS | 1.77.6 |
| **拖拽** | vuedraggable | 2.24.3 |
| **移动端调试** | vconsole | 3.15.1 |

---

## 四、项目目录结构

### 4.1 后端项目结构 ($CMDB_SERVER_LITE)

```
cmdb_server_lite/
├── app/                         # 应用主目录
│   ├── __init__.py             # Flask 应用工厂 create_app()
│   ├── api/                     # API 路由
│   │   └── v1/                 # v1 版本 API
│   │       ├── __init__.py     # register_v1_routes()
│   │       ├── common.py       # 健康检查 / 统计
│   │       ├── classification.py # 分类
│   │       ├── model.py        # 模型 / 实例
│   │       ├── instance.py     # 实例详情 / 关联
│   │       ├── association.py  # 旧版兼容（/find、/create、/delete）
│   │       ├── relation.py     # 对象关联
│   │       └── user.py         # 用户自定义（/api/usercustom/...）
│   ├── config/                  # 配置
│   │   ├── settings.py         # BaseConfig + DevelopmentConfig/TestingConfig/ProductionConfig
│   │   ├── dev.py / prod.py / test.py
│   ├── db/                      # 数据库层
│   │   ├── engine.py           # DatabaseEngine（SQLAlchemy 引擎，仅连接池）
│   │   ├── executor.py         # 原生 SQL 执行器
│   │   ├── dialect.py          # sqlglot 方言转换
│   │   └── sql_loader.py       # .sql 文件加载器
│   ├── sql/                     # SQL 语句目录
│   │   ├── association/        # 关联相关 SQL
│   │   ├── classification/     # 分类相关 SQL
│   │   ├── common/             # 通用 SQL
│   │   ├── instance/           # 实例相关 SQL
│   │   ├── model/              # 模型相关 SQL
│   │   ├── relation/           # 对象关联 SQL
│   │   └── user/               # 用户自定义 SQL
│   ├── service/                 # 业务逻辑
│   │   ├── association_service.py
│   │   ├── classification_service.py
│   │   ├── instance_service.py
│   │   ├── model_service.py
│   │   ├── relation_service.py
│   │   ├── statistics_service.py
│   │   └── user_service.py
│   ├── migrate/                 # 数据库迁移（唯一入口）
│   │   ├── __init__.py
│   │   └── migrate.py          # 建表 + 数据迁移 + 关联初始化
│   ├── middlewares/             # 中间件
│   │   ├── cors.py
│   │   └── request_mw.py
│   ├── utils/                   # 工具
│   │   ├── logger.py
│   │   ├── exceptions.py
│   │   └── tools.py
│   └── logs/                    # 运行日志（app.log）
├── tests/                       # 单元测试
├── .env / .env.prod / .env.test # 环境变量
# Python 版本：3.11 ~ 3.14（可选范围，已移除 .python-version 硬性约束）
├── requirements.txt             # Python 依赖清单
├── run.py                       # 后端启动入口（重要！不是 main.py）
└── cmdb_dev.db                  # 开发数据库文件（运行 migrate 后生成）
```

### 4.2 前端项目结构 ($CMDB_UI_LITE)

```
cmdb_ui_lite/
├── src/
│   ├── api/                     # API 客户端
│   │   ├── client.js           # 统一入口（modelAPI、instanceAPI 等）
│   │   ├── instance.js
│   │   ├── modelAttribute.js
│   │   ├── association.js
│   │   └── user-custom.js
│   ├── assets/                  # 静态资源
│   │   ├── api/models/         # Mock 数据（模型/实例/关联 JSON）
│   │   ├── icon/               # 图标资源
│   │   ├── images/             # 图片资源
│   │   ├── json/               # 配置 JSON
│   │   └── scss/               # 样式文件
│   ├── components/              # 公共组件
│   │   ├── columns-config/     # 列配置
│   │   ├── condition-picker/   # 条件选择器
│   │   ├── filter/             # 筛选组件
│   │   ├── filter-tag/         # 筛选标签
│   │   ├── instance/           # 实例组件（details）
│   │   ├── instance-association/ # 实例关联
│   │   ├── instance-details/   # 实例详情侧滑
│   │   ├── layout/             # 布局（header）
│   │   ├── property/           # 属性组件
│   │   ├── search/             # 搜索组件（按类型：int/bool/enum 等）
│   │   └── ui/                 # 通用 UI（collapse、details、form）
│   ├── views/                   # 页面视图
│   │   ├── business/           # 业务列表 / 拓扑
│   │   ├── general-model/      # 通用模型列表 / 详情
│   │   ├── host/               # 主机视图
│   │   └── resource/           # 资源模型入口
│   ├── router/                  # Vue Router
│   │   └── index.js
│   ├── store/                   # Vuex 状态
│   │   ├── modules/
│   │   ├── filter-store.js
│   │   └── index.js
│   ├── utils/                   # 工具函数
│   │   ├── query-builder.js
│   │   ├── query-operator.js
│   │   └── router-query.js     # 重要！RouterQuery 状态管理
│   ├── App.vue
│   └── main.js
├── tests/                       # Playwright E2E 测试
├── dist/                        # 构建输出（npm run build 后生成）
├── public/                      # 静态模板
├── package.json                 # Node.js 依赖与脚本
├── vue.config.js                # Vue CLI 配置（devServer port=8080, proxy -> 5000）
└── server.js                    # 前端预览 + API 代理（端口 3000）
```

---

## 五、开发流程 SOP

### 标准开发周期

```
需求确认 → 开发实现 → 构建验证 → 服务启动 → Web 测试 → 完成
```

### 1. 需求分析与任务分解

**执行步骤**:
1. 理解需求目标和功能点
2. 确定涉及的项目（前端/后端/两者）
3. 分解任务为可测试的功能点
4. 创建 TodoWrite 任务清单

### 2. 开发实现

**前端开发规范**:
- 使用 Vue 2.7.0 语法（Options API）
- 组件命名: PascalCase（`.vue` 文件名）
- 方法命名: camelCase
- CSS 类名: kebab-case
- `src/utils/router-query.js` 提供 RouterQuery，用于 URL 参数与组件状态同步

**后端开发规范**:
- 使用 Python 3.14.4 + Flask 2.3.3（Werkzeug 2.3.7）
- 数据库操作通过 `app/db/executor.py`（原生 SQL + SQLAlchemy 连接池），**禁用 ORM Model**
- 新建 SQL 语句放在 `app/sql/{模块}/` 下
- 业务逻辑放入 `app/service/*.py`
- RESTful API 设计，v1 版本放在 `app/api/v1/`，路由统一用 Blueprint
- 返回 JSON 格式数据，使用 `APIException` 统一错误处理

**代码注释规范**:
- 函数和方法必须标注输入参数和返回值
- 条件判断旁标注条件逻辑与数据变化
- 复杂循环处标注数据转换过程
- API endpoint 标注请求/响应格式

**API 调用规范**:
```javascript
// 前端 API 调用统一入口
import { modelAPI } from '@/api/client'

// 获取模型实例列表（带分页和搜索）
const result = await modelAPI.listInstances('bk_slb', {
  page: 1,
  page_size: 20,
  search: 'keyword',
  sort: 'id',
  order: 'asc'
})
```

### 3. 构建验证

**前端构建**:
```bash
cd $CMDB_UI_LITE
npm run build   # 输出到 dist/
```

**后端验证**:
```bash
cd $CMDB_SERVER_LITE
# 检查依赖安装
pip list | grep -i flask
python -c "from app import create_app; print('OK')"
```

### 4. 服务启动

**启动后端**:
```bash
cd $CMDB_SERVER_LITE
# 迁移（首次运行或表结构变更时必跑）
python3 -m app.migrate.migrate
# 启动
python3 run.py
# 运行在 http://localhost:5000
# 健康检查: http://localhost:5000/api/v1/common/health
```

**启动前端开发服务器**（带 API 代理到后端 5000）:
```bash
cd $CMDB_UI_LITE
npm run dev
# 运行在 http://localhost:8080
# 代理规则: /api、/health、/find、/create、/delete -> http://localhost:5000
```

**启动前端预览（SOLO Dev 环境）**（重要！必须先构建）:
```bash
cd $CMDB_UI_LITE
npm run build     # 必须先构建到 dist/
node server.js
# 端口: 3000（提供 dist/ 静态文件 + API 代理到 http://localhost:5000）
```

### 5. Web 智能体测试

**重要**: 请参考 [web-test-agent-rules.md](./web-test-agent-rules.md) 获取完整的 Web 测试执行路径和方法。

**快速执行**:

```bash
cd $CMDB_UI_LITE

# 1. 确保服务运行（后端 5000 和前端 3000 都要跑起来）
curl -s http://localhost:5000/api/v1/common/health
curl -s http://localhost:3000/ -o /dev/null -w "%{http_code}"

# 2. 使用本地 Playwright 执行测试
./node_modules/.bin/playwright test tests/demo.spec.js

# 3. UI 模式运行（可视化调试）
./node_modules/.bin/playwright test --ui
```

---

## 六、验收交付标准

| 序号 | 步骤 | 命令 | 说明 |
|------|------|------|------|
| 1 | 后端依赖安装 | `cd $CMDB_SERVER_LITE && pip install -r requirements.txt` | 验证依赖安装 |
| 2 | 数据库迁移 | `cd $CMDB_SERVER_LITE && python3 -m app.migrate.migrate` | 建表 + 初始化数据（包括 cc_AsstDes 标准值 default/belong/connect/group/run） |
| 3 | 前端构建 | `cd $CMDB_UI_LITE && npm run build` | 确保代码无编译错误，输出到 dist/ |
| 4 | 后端启动 | `cd $CMDB_SERVER_LITE && python3 run.py` | API 服务运行在 5000 |
| 5 | 前端预览 | `cd $CMDB_UI_LITE && node server.js` | 预览服务 + API 代理在 3000 |
| 6 | SOLO 预览 | `OpenPreview` 工具 | 实际预览地址通常是 http://localhost:3000 |
| 7 | 用户验收 | 用户确认功能 | 验证功能交互 |

---

## 七、数据库迁移

### 7.1 迁移工具

后端使用 SQLAlchemy + sqlglot 进行数据库迁移：

- **唯一迁移入口**：`python3 -m app.migrate.migrate`（脚本路径：`app/migrate/migrate.py`）
- **功能**：
  - 创建核心表（cc_ObjDes、cc_ObjAttDes、cc_AsstDes、cc_ObjAsst、cc_InstAsst_0_pub）
  - 迁移模型、属性、实例数据
  - 初始化标准关联类型（cc_AsstDes: default / belong / connect / group / run）
  - 初始化对象关联（bk_obj_asst_id 格式：`{源模型ID}_{关联类型ID}_{目标模型ID}`）
  - 迁移实例关联数据

### 7.2 迁移命令

```bash
cd $CMDB_SERVER_LITE

# 标准迁移方式（推荐）
python3 -m app.migrate.migrate

# 清空重建（数据变更后，推荐先删库）
rm cmdb_dev.db
python3 -m app.migrate.migrate
```

### 7.3 数据库配置

**开发环境**（默认）：
```bash
FLASK_ENV=development   # 或不设置，默认 development
DATABASE_TYPE=sqlite
DATABASE_NAME=cmdb_dev.db
```

**生产环境**：
```bash
FLASK_ENV=production
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=cmdb_prod
DATABASE_USER=your_user
DATABASE_PASSWORD=your_password
```

---

## 八、API 端点

### 8.1 API 路由注册结构

| Blueprint | url_prefix | 路径模式 | 说明 |
|-----------|-----------|---------|------|
| `common_bp` | `/api/v1/common` | `/api/v1/common/*` | 健康检查、统计信息 |
| `classification_bp` | `/api/v1/classifications` | `/api/v1/classifications/*` | 分类 |
| `model_bp` | `/api/v1/models` | `/api/v1/models/*` | 模型列表 / 详情 / 属性 |
| `instance_bp` | `/api/v1/instances` | `/api/v1/instances/*` | 实例关联 / 关联实例 |
| `relation_bp` | `/api/v1/relations` | `/api/v1/relations/*` | 对象关联列表 |
| `association_bp` | 无 | `/find/*`, `/create/*`, `/delete/*` | 旧版兼容路由 |
| `user_bp` | 无 | `/api/usercustom/*` | 用户自定义列配置 |

### 8.2 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/common/health` | 健康检查 |
| GET | `/api/v1/common/statistics` | 统计信息 |
| GET | `/api/v1/classifications` | 分类列表 |
| POST | `/api/v1/classifications/find/classificationobject` | 分类对象查询 |
| GET | `/api/v1/models` | 模型列表 |
| GET | `/api/v1/models/{model_id}` | 模型详情 |
| GET | `/api/v1/models/{model_id}/attributes` | 模型属性列表 |
| GET | `/api/v1/models/{model_id}/instances` | 实例列表 |
| POST | `/api/v1/models/{model_id}/instances/search` | 实例搜索 |
| GET | `/api/v1/models/{model_id}/instances/{id}` | 实例详情 |
| GET | `/api/v1/instances/{id}/associations` | 实例关联关系 |
| GET | `/api/v1/instances/{id}/related` | 关联实例 |
| GET | `/api/v1/relations` | 对象关联关系列表 |
| POST | `/find/{obj_id}` | 查询模型实例（旧版兼容） |
| POST | `/find/associationtype` | 查询关联类型 |
| POST | `/find/objectassociation` | 查询对象关联 |
| POST | `/find/instassociation` | 查询实例关联 |
| POST | `/create/instassociation` | 创建实例关联 |
| DELETE | `/delete/instassociation/{obj_id}/{inst_asst_id}` | 删除实例关联 |
| POST | `/api/usercustom/user/search` | 用户配置搜索 |
| POST | `/api/usercustom` | 保存用户配置 |
| GET | `/api/usercustom/model/{model_id}` | 获取模型自定义列配置 |
| POST | `/api/usercustom/model/{model_id}` | 保存模型自定义列配置 |
| GET | `/api/users` | 用户列表 |

---

## 九、常用命令

### 后端命令

```bash
cd $CMDB_SERVER_LITE

# 启动 API 服务
python3 run.py

# 数据库迁移
python3 -m app.migrate.migrate

# 检查依赖
pip list

# 安装依赖
pip install -r requirements.txt

# 运行单元测试
python -m pytest tests/ -v
```

### 前端命令

```bash
cd $CMDB_UI_LITE

npm run build      # 生产构建（必须在预览前执行，输出到 dist/）
node server.js     # 带 API 代理的预览服务（端口 3000）
npm run dev        # Vue CLI 开发服务器（热重载，端口 8080）
npm test           # Playwright E2E 测试
```

### 数据库调试

```bash
cd $CMDB_SERVER_LITE

# 使用 SQLite 命令行（开发环境）
sqlite3 cmdb_dev.db
.tables  # 查看所有表

# 使用 Python 脚本快速验证
python3 << 'EOF'
from app.db.engine import DatabaseEngine
from app.config.settings import get_config
config = get_config('development')
de = DatabaseEngine()
de.init_engine(config)
from sqlalchemy import text
with de._engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    print(result.fetchall())
EOF
```

---

## 十、快速参考路径

### 绝对路径速查

| 路径 | 说明 |
|------|------|
| `/workspace` | 项目根目录 |
| `/workspace/bk-cmdb` | 原项目源码（参考用） |
| `/workspace/cmdb_ui_lite` | 前端子项目 |
| `/workspace/cmdb_server_lite` | 后端子项目 |
| `/workspace/.trae/rules` | 项目规则文档 |

### 相对路径（从项目根目录）

| 相对路径 | 说明 |
|---------|------|
| `./bk-cmdb` | 原项目源码 |
| `./cmdb_ui_lite` | 前端子项目 |
| `./cmdb_server_lite` | 后端子项目 |
| `./.trae/rules` | 项目规则文档 |

---

## 十一、当前运行服务状态

| 服务 | 端口 | 启动命令 | 用途 |
|------|------|---------|------|
| **后端 API** | 5000 | `python3 run.py` | 数据服务 |
| **前端预览 + API 代理** | 3000 | `node server.js` | SOLO 云端访问 + 代理后端 |
| **前端开发服务器** | 8080 | `npm run dev` | Vue CLI 热重载开发模式 |

---

## 十二、端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 5000 | 后端 Flask API | Flask 主服务，所有数据接口 |
| 3000 | 前端预览 + API 代理 | `node server.js` 提供 dist/ 静态文件 + 代理到 5000 |
| 8080 | Vue CLI dev server | `vue.config.js` devServer 配置，带 hot/live reload 及 API 代理 |

---

## 十三、重要文件说明

| 文件路径 | 说明 |
|---------|------|
| `$CMDB_SERVER_LITE/run.py` | **后端启动入口**（不是 main.py），读 `.env` 后 create_app 并运行 |
| `$CMDB_SERVER_LITE/app/__init__.py` | Flask 应用工厂 `create_app()`，注册所有 Blueprint + 全局错误处理 |
| `$CMDB_SERVER_LITE/app/config/settings.py` | 配置文件（BaseConfig / DevelopmentConfig / TestingConfig / ProductionConfig） |
| `$CMDB_SERVER_LITE/app/db/engine.py` | SQLAlchemy 引擎管理（DatabaseEngine 单例，仅连接池） |
| `$CMDB_SERVER_LITE/app/db/executor.py` | 原生 SQL 执行器（`query_all`、`query_one`、`execute`） |
| `$CMDB_SERVER_LITE/app/migrate/migrate.py` | **唯一数据库迁移入口**（建表 + 预置关联类型 + 数据初始化） |
| `$CMDB_SERVER_LITE/requirements.txt` | Python 依赖清单（含 Flask 2.3.3、SQLAlchemy>=2.0.35、sqlglot 19.8.0） |
| `$CMDB_SERVER_LITE/.python-version` | **3.14.4**，必须匹配当前 Python 版本 |
| `$CMDB_UI_LITE/server.js` | 前端预览 + API 代理服务器（端口 3000） |
| `$CMDB_UI_LITE/vue.config.js` | Vue CLI 配置（devServer 端口 8080，API 代理规则） |
| `$CMDB_UI_LITE/package.json` | Node.js 依赖 + npm scripts（dev/build/test/serve 等） |
| `$CMDB_UI_LITE/src/utils/router-query.js` | RouterQuery 状态管理（URL 参数与组件状态同步） |

---

## 十四、RouterQuery 状态管理

### 概述

`src/utils/router-query.js` 提供 CMDB UI Lite 的 URL 参数状态管理工具，用于实现组件状态与 URL 参数的同步。

### API 方法

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `get(key, defaultValue)` | 获取单个参数 | key: string, defaultValue?: any | any |
| `getAll()` | 获取所有参数 | - | Object |
| `set(key, value)` | 设置单个参数或批量设置 | key: string\|Object, value?: any | void |
| `setAll(query)` | 替换所有参数 | query: Object | void |
| `delete(key)` | 删除单个参数 | key: string | void |
| `refresh()` | 刷新页面（添加时间戳） | - | void |
| `clear()` | 清除所有参数 | - | void |
| `getAs(key, type, defaultValue)` | 获取并转换类型 | key: string, type: 'int'\|'float'\|'bool', defaultValue: any | any |

---

## 十五、常见问题排查

### 1. 后端无法启动 / 端口被占用

```bash
# 检查端口占用
lsof -i :5000
# 或
netstat -tlnp | grep 5000

# 杀死占用进程
kill -9 <PID>
```

### 2. Python 版本不匹配

**错误**: `ModuleNotFoundError`、`SyntaxError` 或导入失败

**检查**:
```bash
python3 --version            # 应输出 3.14.4
cat $CMDB_SERVER_LITE/.python-version
```

### 3. 数据库连接失败

**检查**:
```bash
# 检查数据库文件是否存在
ls -la $CMDB_SERVER_LITE/cmdb_dev.db

# 检查数据库配置
cat $CMDB_SERVER_LITE/.env
```

### 4. 迁移失败 / 表已存在 / 数据不一致

```bash
# 删除数据库重新迁移（推荐）
rm $CMDB_SERVER_LITE/cmdb_dev.db
cd $CMDB_SERVER_LITE && python3 -m app.migrate.migrate
```

### 5. 前端预览 404 / 白屏

**错误原因**: 忘记执行 `npm run build`，`dist/` 为空

**解决**:
```bash
cd $CMDB_UI_LITE
npm run build    # 必须先生成 dist/
node server.js   # 然后启动预览
```

### 6. API 返回 500 错误

**检查日志**:
```bash
# 查看后端控制台输出（run.py 运行窗口）
# 或查看文件日志
tail -f $CMDB_SERVER_LITE/app/logs/app.log
```

### 7. 前端 API 请求失败（代理问题）

**检查代理规则**:

- Vue CLI dev（8080）: `vue.config.js` 的 `devServer.proxy`，代理路径 `/api`、`/health`、`/find`、`/create`、`/delete`
- Node 预览（3000）: `server.js` 的 `proxyToBackend()`，同样代理上述路径

**确保后端在 5000 正常运行**:
```bash
curl -s http://localhost:5000/api/v1/common/health
```

---

## 十六、Web 智能体测试依赖安装规则

### 概述

当 Web 智能体测试需要 Python、Node.js/npm、Chromium 等依赖时，应优先使用国内镜像源安装。如果 Chromium 无法安装或使用，依次尝试 Firefox 或 Chrome CDP。

### 依赖安装优先级

```
1. Python 依赖（优先使用国内 pip 镜像）
   ↓ 如果失败
2. Node.js/npm 依赖（优先使用 npmmirror 镜像）
   ↓ 如果失败
3. Chromium 浏览器（优先使用 Playwright 内置）
   ↓ 如果失败
4. Firefox 浏览器（Playwright 支持）
   ↓ 如果失败
5. Chrome CDP 协议（连接已安装的 Chrome）
```

### 国内镜像源

| 依赖 | 镜像名称 | URL |
|------|---------|-----|
| **pip/PyPI** | 清华 | https://pypi.tuna.tsinghua.edu.cn/simple |
| **pip/PyPI** | 阿里云 | https://mirrors.aliyun.com/pypi/simple/ |
| **npm** | npmmirror | https://registry.npmmirror.com |
| **Chromium** | npmmirror | https://npmmirror.com/mirrors/playwright |

---

## 十七、注意事项

1. **后端启动**：必须使用 `python3 run.py`，不要使用 `python3 main.py`
2. **Python 版本**：支持 `3.11` ~ `3.14`（可选范围，已移除 `.python-version` 硬性约束），SQLAlchemy 需 `>=2.0.35` 才支持
3. **数据库迁移**：`python3 -m app.migrate.migrate`；变更数据模型后，删除旧 `cmdb_dev.db` 重新迁移更干净
4. **前端构建**：预览前必须先执行 `npm run build`，否则 `dist/` 为空，预览全 404
5. **API 端口**：后端 5000，前端代理 3000，Vue CLI dev 模式 8080；所有 API 最终都发往后端 5000
6. **环境变量**：使用 `.env`（开发）、`.env.prod`、`.env.test` 管理，不要硬编码
7. **关联关系**：
   - `cc_AsstDes.bk_asst_id` 标准值：`default` / `belong` / `connect` / `group` / `run`
   - `bk_obj_asst_id` 格式：`{源模型ID}_{关联类型ID}_{目标模型ID}`（例：`bk_slb_default_bk_slb_server`）
   - 关联描述：`src_des`（源→目标）、`dest_des`（目标→源）、`direction`（方向）
8. **路由前缀**：v1 主要 API 使用 `/api/v1/*`，旧版兼容路由 `/find|/create|/delete` 无前缀，用户自定义走 `/api/usercustom/*`
9. **依赖版本**：所有依赖版本见 `requirements.txt` 和 `package.json`，禁止随意升级（尤其是 Flask / SQLAlchemy / Vue / bk-magic-vue）
10. **API 响应格式**：所有 API 必须使用 BaseResp 规范，业务错误不使用 HTTP 404/400，详见第十八节
11. **前端 HTTP 请求**：禁止直接使用 `this.$http`、`axios` 或 `fetch`，必须通过 `src/api/` 下的公共 API 模块，详见第十九节

---

## 十八、API 规范（BaseResp）

### 概述

与原项目蓝鲸 CMDB 保持一致，所有 API 响应必须使用 **BaseResp** 统一格式，业务逻辑错误通过 `result: false` 区分，不依赖 HTTP 状态码。

### 响应格式

```json
// 成功响应
{
    "result": true,
    "bk_error_code": 0,
    "bk_error_msg": "",
    "data": { ... }  // 业务数据
}

// 错误响应
{
    "result": false,
    "bk_error_code": 1199019,  // 错误码
    "bk_error_msg": "模型不存在"  // 错误信息
}
```

### HTTP 状态码规则

| 场景 | HTTP 状态码 | 说明 |
|------|------------|------|
| 业务成功 | 200 | `result: true` |
| 业务错误 | 200 | `result: false` + `bk_error_code` |
| 认证失败 | 401 | 未登录或 Token 失效 |
| 权限不足 | 403 | 无操作权限 |
| 路由不存在 | 200 | `result: false` + `bk_error_code: 1199019` |

**禁止**：业务逻辑错误使用 HTTP 404、400、500 等状态码。

### 后端实现

#### 统一响应辅助函数

每个 API 模块必须提供 `success_response` 和 `error_response` 辅助函数：

```python
# app/api/v1/model.py

def success_response(data=None, message=''):
    """统一成功响应格式 - 与原项目 BaseResp 一致"""
    if data is None:
        data = {}
    return jsonify({
        'result': True,
        'bk_error_code': 0,
        'bk_error_msg': message,
        'data': data
    }), 200

def error_response(message, error_code=1199999):
    """统一错误响应格式 - 与原项目 BaseResp 一致"""
    return jsonify({
        'result': False,
        'bk_error_code': error_code,
        'bk_error_msg': message
    }), 200
```

#### 异常类定义

```python
# app/utils/exceptions.py

class APIException(Exception):
    """API 异常基类 - 输出与原项目 BaseResp 格式一致"""

    def __init__(self, message: str, status_code: int = 200, error_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or CCErrorCode.CCErrCommParamsInvalid

    def to_dict(self):
        return {
            'result': False,
            'bk_error_code': self.error_code,
            'bk_error_msg': self.message
        }

class NotFoundException(APIException):
    """资源不存在异常 - 返回 200 + BaseResp 格式"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=200, error_code=CCErrorCode.CCErrCommNotFound)
```

#### 全局错误处理

```python
# app/__init__.py

@app.errorhandler(APIException)
def handle_api_exception(e):
    return jsonify(e.to_dict()), e.status_code

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({
        'result': False,
        'bk_error_code': 1199019,
        'bk_error_msg': '请求路径不存在'
    }), 200

@app.errorhandler(500)
def handle_server_error(e):
    return jsonify({
        'result': False,
        'bk_error_code': 1199999,
        'bk_error_msg': '服务器内部错误'
    }), 200
```

### 前端响应拦截器

```javascript
// src/api/client.js

http.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data !== null && typeof data === 'object' && 'result' in data) {
      if (data.result === false) {
        // 业务错误：抛出异常
        const error = new Error(data.bk_error_msg || '业务处理失败')
        error.response = { data }
        return Promise.reject(error)
      }
      // 成功：返回 data 字段内容
      return data.data !== undefined ? data.data : data
    }
    return data
  },
  (error) => {
    return Promise.reject(error)
  }
)
```

### 错误码规范

| 错误码范围 | 说明 |
|-----------|------|
| 0 | 成功 |
| 1199000 - 1199999 | 通用错误 |
| 1199001 | 参数错误 |
| 1199006 | 请求格式错误 |
| 1199019 | 资源不存在 |
| 1199999 | 服务器内部错误 |

---

## 十九、前端 HTTP 请求规范

### 概述

前端项目统一使用 `src/api/` 下的公共 API 模块进行 HTTP 请求，**禁止**在组件中直接使用 `this.$http`、`axios` 或 `fetch`。

### API 模块职责划分

| API 模块 | 文件路径 | 职责 |
|---------|---------|------|
| `modelAPI` | `src/api/client.js` | 模型管理、实例 CRUD、分类、属性 |
| `topoAPI` | `src/api/topo.js` | 业务列表、拓扑树、主机转移 |
| `associationAPI` | `src/api/association.js` | 实例关联、对象关联 |
| `instanceAPI` | `src/api/instance.js` | 实例查询（旧版兼容） |
| `userCustomAPI` | `src/api/user-custom.js` | 用户自定义配置 |

### 使用规范

#### ✅ 正确示例

```javascript
// 在组件中使用公共 API
import { modelAPI } from '@/api/client'
import { topoAPI } from '@/api/topo'

export default {
  methods: {
    async loadModels() {
      const data = await modelAPI.getModels()
      this.models = data.models
    },
    async loadBizList() {
      const data = await topoAPI.getBizList()
      this.bizList = data
    }
  }
}
```

#### ❌ 错误示例

```javascript
// 禁止直接使用 this.$http
async loadBizList() {
  const data = await this.$http.get('biz/simplify')  // ❌ 错误
}

// 禁止直接导入 axios
import axios from 'axios'
async loadBizList() {
  const res = await axios.get('/api/v1/topo/biz')  // ❌ 错误
}

// 禁止使用 fetch
async loadBizList() {
  const res = await fetch('/api/v1/topo/biz')  // ❌ 错误
}
```

### 新增 API 流程

1. **确定 API 模块**：根据功能选择合适的 API 模块文件
2. **添加 API 方法**：在模块中新增方法，复用 `http` 实例
3. **组件调用**：导入并调用新增的 API 方法

```javascript
// 步骤 1-2: 在 src/api/topo.js 中添加新方法
export const topoAPI = {
  // ... 现有方法

  // 新增：获取业务详情
  getBizDetail(bizId) {
    return http.get(`/api/v1/topo/biz/${bizId}`)
  }
}

// 步骤 3: 在组件中调用
import { topoAPI } from '@/api/topo'

async loadBizDetail() {
  const data = await topoAPI.getBizDetail(this.bizId)
  this.bizDetail = data
}
```

### Vuex Store 中使用 API

```javascript
// src/store/modules/objectModelClassify.js
import { modelAPI } from '@/api/client'

const actions = {
  async getClassifications({ commit }) {
    try {
      const data = await modelAPI.getClassifications()
      commit('setClassifications', data.classifications)
    } catch (error) {
      console.error(error.message)
    }
  }
}
```

### 错误处理

响应拦截器会自动处理 BaseResp 格式，业务错误会抛出异常：

```javascript
async loadData() {
  try {
    const data = await modelAPI.getModel(this.modelId)
    this.model = data
  } catch (error) {
    // error.message 包含 bk_error_msg
    this.$bkMessage({ message: error.message, theme: 'error' })
  }
}
```

---

## 二十、Store 规范（Vuex）

### 概述

使用 Vuex 进行状态管理，将全局状态和业务状态统一存放在 `src/store/` 目录下。

### Store 目录结构

```
src/store/
├── modules/              # 业务模块
│   ├── global.js        # 全局状态（业务列表等）
│   ├── object-biz.js    # 业务相关状态
│   ├── objectModelClassify.js  # 模型分类状态
│   └── userCustom.js    # 用户自定义配置
├── filter-store.js      # 筛选状态管理
└── index.js             # Store 入口
```

### 模块规范

```javascript
// src/store/modules/example.js

const state = {
  items: [],
  loading: false
}

const mutations = {
  setItems(state, items) {
    state.items = items
  },
  setLoading(state, loading) {
    state.loading = loading
  }
}

const actions = {
  async fetchItems({ commit }) {
    commit('setLoading', true)
    try {
      const data = await modelAPI.getItems()
      commit('setItems', data.items)
    } catch (error) {
      console.error(error.message)
    } finally {
      commit('setLoading', false)
    }
  }
}

const getters = {
  itemCount: state => state.items.length
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
}
```

### 在组件中使用 Store

```javascript
import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  computed: {
    ...mapState('example', ['items', 'loading']),
    ...mapGetters('example', ['itemCount'])
  },
  methods: {
    ...mapActions('example', ['fetchItems'])
  },
  created() {
    this.fetchItems()
  }
}
```

### Store 与 API 的关系

- **Store** 负责状态管理和缓存
- **API** 负责实际的 HTTP 请求
- Store 的 actions 调用 API 模块，不直接发起 HTTP 请求

---

**文档维护**：本文档随代码更新，请保持同步。
- **最后更新**：2026-07-20
- **更新内容**：
  - 2026-07-20：新增 API 规范（BaseResp）、Store 规范、HTTP 请求规范
  - 2026-06-08：修正 Python 版本为 3.14.4，更正前后端目录结构与实际一致，补充 Blueprint 路由注册结构与 API 端点，修正端口说明、迁移命令、关联 ID 格式等。
