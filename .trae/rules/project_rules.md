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
│   │   ├── ui/          # 原项目 UI
│   │   └── .../
│   └── docs/            # 原项目文档
├── cmdb_ui_lite/         # 前端子项目 (Vue 2 + bk-magic-vue)
└── cmdb_server_lite/    # 后端子项目 (Python + Flask + SQLAlchemy)
```

---

## 二、项目概述

### 前端项目 (cmdb_ui_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Vue 2 + bk-magic-vue + Vue Router + Vuex + Axios |
| 构建工具 | Vue CLI |
| 端口 | 3000 (预览)、开发服务器动态端口 |

### 后端项目 (cmdb_server_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Python 3.9.20 + Flask 2.3.3 + SQLAlchemy 2.0.35 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) / MySQL (可选) |
| 端口 | 5000 |
| API 前缀 | `/api/v1` |
| 健康检查 | `http://localhost:5000/api/v1/common/health` |

---

## 三、技术栈详情

### 3.1 后端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Python** | Python | 3.9.20 | 固定版本（见 .python-version） |
| **Web框架** | Flask | 2.3.3 | 轻量级 Web 框架 |
| **数据库ORM** | SQLAlchemy | >=2.0.35 | 仅使用连接池，不使用 ORM Model |
| **方言转换** | sqlglot | 19.8.0 | 多数据库 SQL 方言处理 |
| **环境变量** | python-dotenv | 1.0.0 | 环境变量管理 |
| **日志** | coloredlogs | 15.0.1 | 彩色日志输出 |
| **PostgreSQL驱动** | psycopg2-binary | 2.9.7 | PostgreSQL 数据库驱动 |
| **MySQL驱动** | pymysql | 1.1.0 | MySQL 数据库驱动 |
| **测试** | pytest | 7.4.2 | Python 单元测试框架 |

### 3.2 前端技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| **框架** | Vue | 2.x |
| **UI库** | bk-magic-vue | 最新 |
| **路由** | Vue Router | 3.x |
| **状态管理** | Vuex | 3.x |
| **HTTP客户端** | Axios | 最新 |
| **构建工具** | Vue CLI | 5.x |

---

## 四、项目目录结构

### 4.1 后端项目结构 ($CMDB_SERVER_LITE)

```
cmdb_server_lite/
├── app/                        # 应用主目录
│   ├── __init__.py            # Flask 应用工厂
│   ├── config/                 # 配置目录
│   │   ├── __init__.py
│   │   └── settings.py        # 配置文件
│   ├── db/                     # 数据库目录
│   │   ├── __init__.py
│   │   ├── engine.py          # SQLAlchemy 引擎管理
│   │   ├── executor.py        # 原生 SQL 执行器
│   │   └── sql/               # SQL 语句目录
│   │       ├── model/         # 模型相关 SQL
│   │       ├── instance/      # 实例相关 SQL
│   │       ├── association/   # 关联相关 SQL
│   │       ├── classification/ # 分类相关 SQL
│   │       └── user/          # 用户相关 SQL
│   ├── api/                    # API 目录
│   │   └── v1/                # v1 版本 API
│   │       ├── __init__.py    # 路由注册
│   │       ├── common.py      # 通用 API
│   │       ├── classification.py # 分类 API
│   │       ├── model.py       # 模型 API
│   │       ├── instance.py    # 实例 API
│   │       ├── association.py # 关联 API
│   │       ├── relation.py    # 关系 API
│   │       └── user.py        # 用户 API
│   ├── service/               # 业务逻辑目录
│   │   ├── __init__.py
│   │   ├── model_service.py   # 模型服务
│   │   ├── instance_service.py # 实例服务
│   │   ├── association_service.py # 关联服务
│   │   └── user_service.py    # 用户服务
│   ├── migrate/               # 迁移工具目录
│   │   ├── __init__.py
│   │   └── migrate.py        # 数据库迁移工具
│   ├── middlewares/           # 中间件目录
│   │   └── cors.py           # CORS 中间件
│   └── utils/                 # 工具目录
│       ├── logger.py          # 日志工具
│       └── exceptions.py      # 自定义异常
├── .venv/                     # Python 虚拟环境
├── .env                       # 环境变量文件
├── .env.prod                  # 生产环境变量
├── .env.test                  # 测试环境变量
├── .python-version            # Python 版本文件
├── run.py                     # 启动入口（重要！）
├── requirements.txt           # Python 依赖
└── cmdb_dev.db               # 开发数据库文件
```

### 4.2 前端项目结构 ($CMDB_UI_LITE)

```
cmdb_ui_lite/
├── src/
│   ├── api/                # API 客户端
│   │   ├── client.js       # API 统一入口
│   │   ├── instance.js     # 实例相关 API
│   │   ├── modelAttribute.js # 模型属性 API
│   │   └── association.js  # 关联关系 API
│   ├── assets/             # 静态资源
│   │   ├── json/           # Mock 数据
│   │   └── scss/           # 样式文件
│   ├── components/         # 公共组件
│   │   ├── filter/         # 筛选组件
│   │   ├── property/       # 属性组件
│   │   └── search/         # 搜索组件
│   ├── views/              # 页面视图
│   │   ├── business/       # 业务视图
│   │   ├── general-model/  # 通用模型视图
│   │   ├── host/           # 主机视图
│   │   └── resource/       # 资源视图
│   ├── router/             # 路由配置
│   └── store/              # Vuex 状态
├── tests/                  # 测试文件
│   └── e2e/               # E2E 测试
│       ├── specs/         # 测试用例
│       └── page-objects/  # 页面对象
├── dist/                   # 构建输出
├── package.json
└── server.js              # API 代理服务器
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
- 使用 Vue 2 语法
- 组件命名: PascalCase
- 方法命名: camelCase
- CSS 类名: kebab-case

**后端开发规范**:
- 使用 Python 3.9.20 + Flask 2.3.3
- 数据库操作使用 SQLAlchemy 2.0+ 连接池
- 原生 SQL 执行，不使用 ORM Model
- RESTful API 设计
- 返回 JSON 格式数据

**代码注释规范**:
所有代码必须添加注释，遵循以下规则：

1. **函数和方法注释** - 必须标注输入参数和输出
2. **条件判断注释** - 标注条件逻辑和数据变化
3. **循环处理注释** - 标注数据转换过程
4. **API端点注释** - 标注请求和响应格式

**API 调用规范**:
```javascript
// 前端 API 调用
import { modelAPI } from '@/api/client'

// 获取模型实例列表
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
npm run build
```

**后端验证**:
```bash
cd $CMDB_SERVER_LITE
# 检查依赖安装
.venv/bin/pip list
```

### 4. 服务启动

**启动后端**:
```bash
cd $CMDB_SERVER_LITE
source .venv/bin/activate
python3 run.py
# 运行在 http://localhost:5000
# 健康检查: http://localhost:5000/api/v1/common/health
```

**启动前端开发服务器**:
```bash
cd $CMDB_UI_LITE
npm run dev
```

**启动前端预览（SOLO Dev 环境）**:
```bash
cd $CMDB_UI_LITE
npm run build
node server.js
# 端口: 3000 (带 API 代理)
```

### 5. Web 智能体测试

**重要**: 请参考 [web-test-agent-rules.md](./web-test-agent-rules.md) 获取完整的 Web 测试执行路径和方法。

**快速执行**:

```bash
cd $CMDB_UI_LITE

# 1. 确保服务运行
curl -s http://localhost:5000/api/v1/common/health
curl -s http://localhost:3000/ -o /dev/null -w "%{http_code}"

# 2. 使用本地 Playwright 执行测试
./node_modules/.bin/playwright test tests/demo.spec.js

# 3. UI 模式运行
./node_modules/.bin/playwright test --ui
```

---

## 六、验收交付标准

### 每次开发任务完成后必须完成以下步骤

| 序号 | 步骤 | 前端命令 | 后端命令 | 说明 |
|------|------|----------|----------|------|
| 1 | 后端构建 | - | `.venv/bin/pip install -r requirements.txt` | 依赖安装验证 |
| 2 | 数据库迁移 | - | `python3 -m app.migrate.migrate` | 数据迁移验证 |
| 3 | 前端构建 | `npm run build` | - | 确保代码无编译错误 |
| 4 | 后端启动 | - | `.venv/bin/python3 run.py` | API 服务运行 |
| 5 | 前端预览 | `node server.js` | - | 预览服务运行 |
| 6 | SOLO 预览 | 使用 `OpenPreview` | - | 报告实际预览地址给用户 |
| 7 | 用户验收 | 用户确认功能 | - | 验证功能交互 |

---

## 七、数据库迁移

### 7.1 迁移工具

后端使用 SQLAlchemy + sqlglot 进行数据库迁移：

- **迁移入口**：`python3 -m app.migrate.migrate`
- **功能**：
  - 创建核心表（cc_ObjDes、cc_ObjAttDes、cc_AsstDes、cc_ObjAsst、cc_InstAsst_0_pub）
  - 迁移模型数据
  - 迁移属性数据（自动处理 option 字段序列化）
  - 创建实例表
  - 迁移实例数据
  - 迁移关联关系数据

### 7.2 迁移命令

```bash
cd $CMDB_SERVER_LITE

# 方法1: 使用 Python 模块方式
.venv/bin/python3 -m app.migrate.migrate

# 方法2: 直接运行迁移脚本
.venv/bin/python3 app/migrate/migrate.py

# 方法3: 单独迁移关联关系
.venv/bin/python3 migrate_associations.py
```

### 7.3 数据库配置

**开发环境**（默认）：
```bash
FLASK_ENV=development  # 或不设置
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

### 8.1 API 版本

| 版本 | 前缀 | 说明 |
|------|------|------|
| v1 | `/api/v1` | 当前版本 |

### 8.2 API 端点列表

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
| GET | `/api/v1/relations` | 关联关系列表 |
| GET | `/api/usercustom/model/{model_id}` | 用户自定义配置 |
| POST | `/api/usercustom/model/{model_id}` | 保存用户自定义配置 |

---

## 九、常用命令

### 后端命令

```bash
cd $CMDB_SERVER_LITE

# 激活虚拟环境
source .venv/bin/activate

# 启动 API 服务
python3 run.py

# 数据库迁移
python3 -m app.migrate.migrate

# 单独迁移关联关系
python3 migrate_associations.py

# 检查依赖
.venv/bin/pip list

# 安装依赖
.venv/bin/pip install -r requirements.txt
```

### 前端命令

```bash
cd $CMDB_UI_LITE

npm run build                    # 生产构建（必须在预览前执行）
node server.js                   # 带 API 代理的预览服务（端口 3000）
npm run dev                      # 开发服务器（热重载）
```

### 数据库调试

```bash
cd $CMDB_SERVER_LITE

# 使用 SQLite 命令行（开发环境）
sqlite3 cmdb_dev.db

# 使用 Python 脚本
.venv/bin/python3 << 'EOF'
from app.db.engine import get_connection
conn = get_connection()
result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(result.fetchall())
conn.close()
EOF
```

---

## 十、快速参考路径

### 绝对路径速查

| 路径 | 说明 |
|------|------|
| `/workspace` | 项目根目录 |
| `/workspace/bk-cmdb` | 原项目源码 |
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

| 服务 | 端口 | 状态 | 用途 |
|------|------|------|------|
| **后端API** | 5000 | ✅ 运行中 | 数据服务 |
| **API代理** | 3000 | ✅ 运行中 | SOLO云端访问后端 |
| **前端开发服务器** | 3001 | ✅ 运行中 | 本地热重载开发 |

---

## 十二、端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 5000 | 后端 API | Flask 服务（主端口） |
| 3000 | 前端预览 + API代理 | `node server.js` 提供静态文件 + API 代理 |
| 3001 | 开发服务器 | Vue CLI 开发模式（热重载） |

---

## 十三、重要文件说明

| 文件路径 | 说明 |
|---------|------|
| `$CMDB_SERVER_LITE/run.py` | **后端启动入口**（不是 main.py） |
| `$CMDB_SERVER_LITE/app/__init__.py` | Flask 应用工厂 |
| `$CMDB_SERVER_LITE/app/config/settings.py` | 配置文件 |
| `$CMDB_SERVER_LITE/app/db/engine.py` | 数据库引擎管理 |
| `$CMDB_SERVER_LITE/app/migrate/migrate.py` | 数据库迁移工具 |
| `$CMDB_SERVER_LITE/.python-version` | Python 版本（3.9.20） |
| `$CMDB_SERVER_LITE/requirements.txt` | Python 依赖清单 |
| `$CMDB_UI_LITE/server.js` | 前端代理服务器 |

---

## 十四、RouterQuery 状态管理

### 概述

RouterQuery 是 CMDB UI Lite 中的 URL 参数状态管理工具，用于实现组件状态与 URL 参数的同步。

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

### 1. 后端无法启动

**错误**：端口已被占用
```bash
# 检查端口占用
lsof -i :5000

# 杀死占用进程
kill -9 <PID>
```

### 2. 数据库连接失败

**检查**：
```bash
# 检查数据库文件是否存在
ls -la cmdb_dev.db

# 检查数据库配置
cat .env
```

### 3. 迁移失败

**错误**：表已存在
```bash
# 删除数据库重新迁移
rm cmdb_dev.db
python3 -m app.migrate.migrate
```

### 4. API 返回 500 错误

**检查日志**：
```bash
# 查看后端控制台输出
tail -f app.log
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
|------|----------|-----|
| **pip/PyPI** | 清华 | https://pypi.tuna.tsinghua.edu.cn/simple |
| **pip/PyPI** | 阿里云 | https://mirrors.aliyun.com/pypi/simple/ |
| **npm** | npmmirror | https://registry.npmmirror.com |
| **Chromium** | npmmirror | https://npmmirror.com/mirrors/playwright |

---

## 十七、注意事项

1. **后端启动**：必须使用 `python3 run.py`，不要使用 `python3 main.py`
2. **数据库迁移**：先激活虚拟环境 `.venv/bin/activate`，再执行迁移
3. **前端构建**：预览前必须先执行 `npm run build`
4. **API 端口**：后端在 5000 端口，前端代理在 3000 端口
5. **环境变量**：使用 `.env` 文件管理环境变量，不要硬编码
6. **版本固定**：Python 版本必须使用 3.9.20（见 .python-version）
7. **依赖版本**：所有依赖版本见 requirements.txt，禁止随意升级

---

**文档维护**：本文档随代码更新，请保持同步。
- **最后更新**：2026-05-29
- **更新内容**：后端重构，从 FastAPI/DuckDB 迁移到 Flask/SQLAlchemy，多数据库支持
