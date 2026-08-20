# CMDB Server Lite 重构计划文档

## 项目概述

本项目基于 `new-frame-plan.txt` 的需求，将现有的 FastAPI + DuckDB 架构重构为 Flask + SQLAlchemy + sqlglot 架构，实现：
- Flask Web 框架
- SQL 语句独立文件管理
- sqlglot 多数据库方言处理
- SQLAlchemy 仅做连接池和原生 SQL 执行（禁用 ORM Model）
- 兼容 PostgreSQL/MySQL/SQLite/SQLite

## 目录结构调整

### 当前完成的结构

```
cmdb_server_lite/
├── app/                    # 核心源码 (新增)
│   ├── __init__.py        # Flask 应用工厂
│   ├── config/            # 配置中心
│   │   ├── __init__.py
│   │   ├── settings.py    # 全局基础配置
│   │   ├── dev.py         # 开发环境配置
│   │   ├── test.py        # 测试环境配置
│   │   └── prod.py        # 生产环境配置
│   ├── api/               # API 路由层
│   │   ├── __init__.py
│   │   └── v1/           # API v1 版本
│   │       ├── __init__.py
│   │       └── common.py  # 公共接口
│   ├── service/           # 业务逻辑层
│   │   └── __init__.py
│   ├── db/                # 数据库核心层
│   │   ├── __init__.py
│   │   ├── engine.py      # SQLAlchemy 引擎管理
│   │   ├── dialect.py     # sqlglot 方言转译
│   │   ├── executor.py    # 原生 SQL 执行器
│   │   └── sql_loader.py  # SQL 文件加载器
│   ├── sql/               # 独立 SQL 文件目录
│   │   ├── common/       # 公共 SQL
│   │   │   ├── page_limit.sql
│   │   │   ├── select_classifications.sql
│   │   │   ├── select_models.sql
│   │   │   └── select_model_attributes.sql
│   │   ├── user/         # 用户模块 SQL (待实现)
│   │   └── order/        # 订单模块 SQL (待实现)
│   ├── utils/             # 全局工具类
│   │   ├── __init__.py
│   │   ├── logger.py     # 日志初始化
│   │   ├── exceptions.py # 自定义业务异常
│   │   └── tools.py      # 通用工具函数
│   ├── middlewares/       # 中间件
│   │   ├── __init__.py
│   │   ├── cors.py       # 跨域中间件
│   │   └── request_mw.py # 请求日志/入参校验
│   ├── migrate/           # 数据库迁移
│   │   └── __init__.py
│   ├── static/            # 静态资源
│   └── templates/         # 模板页面
├── logs/                  # 日志目录 (新增)
├── tests/                 # 测试目录 (新增)
│   ├── __init__.py
│   ├── test_db.py        # 数据库测试
│   └── test_api.py       # API 测试
├── docs/                  # 项目文档
├── dev-action/            # 开发工具 (新增)
│   ├── debug_sqlglot.py     # SQLglot 调试工具
│   └── debug_sqlalchemy.py  # SQLAlchemy 调试工具
├── .env                   # 开发环境变量 (新增)
├── .env.prod              # 生产环境变量 (新增)
├── .env.test              # 测试环境变量 (新增)
├── requirements.txt       # 依赖清单 (新增)
├── run.py                 # 项目启动入口 (新增)
├── README.md             # 项目说明 (新增)
├── cmdb_dev.db           # SQLite dev 数据库 (新增)
├── main.py               # 旧版本入口 (保留)
└── migrate_data.py       # 数据迁移脚本 (保留)
```

## 模块规划

### 1. API 路由层 (app/api)

#### 1.1 公共接口 (common)
- `GET /api/v1/common/health` - 健康检查
- `GET /api/v1/common/statistics` - 统计数据

#### 1.2 分类接口 (classification) - 待实现
- `GET /api/v1/classifications` - 获取所有分类
- `GET /api/v1/classifications/{id}` - 获取单个分类
- `GET /api/v1/classifications/{id}/models` - 获取分类下的模型

#### 1.3 模型接口 (model) - 待实现
- `GET /api/v1/models` - 获取所有模型
- `GET /api/v1/models/{id}` - 获取单个模型
- `GET /api/v1/models/{id}/attributes` - 获取模型属性
- `GET /api/v1/models/{id}/instances` - 获取模型实例列表
- `POST /api/v1/models/{id}/instances` - 创建实例
- `PUT /api/v1/models/{id}/instances/{id}` - 更新实例
- `DELETE /api/v1/models/{id}/instances` - 删除实例

#### 1.4 关联接口 (association) - 待实现
- `GET /api/v1/associations` - 获取所有关联
- `POST /api/v1/associations` - 创建关联
- `DELETE /api/v1/associations/{id}` - 删除关联

### 2. 服务层 (app/service)

#### 2.1 分类服务 (classification_service)
- `get_all_classifications()` - 获取所有分类
- `get_classification_by_id(id)` - 根据 ID 获取分类
- `get_models_by_classification(classification_id)` - 获取分类下的模型

#### 2.2 模型服务 (model_service)
- `get_all_models()` - 获取所有模型
- `get_model_by_id(model_id)` - 获取模型详情
- `get_model_attributes(model_id)` - 获取模型属性
- `get_model_instances(model_id, page, page_size, filters)` - 获取模型实例

#### 2.3 实例服务 (instance_service)
- `create_instance(model_id, data)` - 创建实例
- `update_instance(model_id, instance_id, data)` - 更新实例
- `delete_instance(model_id, instance_ids)` - 删除实例
- `search_instances(model_id, conditions)` - 搜索实例

#### 2.4 关联服务 (association_service)
- `create_association(source_model, source_id, target_model, target_id, relation_type)` - 创建关联
- `delete_association(association_id)` - 删除关联
- `get_instance_associations(instance_id)` - 获取实例关联

### 3. 数据库层 (app/db)

#### 3.1 引擎管理 (engine.py)
- 单例模式管理 SQLAlchemy 引擎
- 支持多数据库类型（SQLite/PostgreSQL/MySQL）
- 连接池配置

#### 3.2 方言转译 (dialect.py)
- sqlglot 多方言支持
- SQL 语法转译（PostgreSQL ↔ SQLite ↔ MySQL）
- SQL AST 解析

#### 3.3 SQL 执行器 (executor.py)
- 参数化查询
- 事务管理
- CRUD 操作封装

#### 3.4 SQL 加载器 (sql_loader.py)
- 独立 SQL 文件管理
- SQL 模板缓存
- 模块化 SQL 组织

### 4. 工具层 (app/utils)

#### 4.1 日志 (logger.py)
- 统一日志配置
- 控制台和文件输出
- 彩色日志格式

#### 4.2 异常 (exceptions.py)
- APIException - 基础 API 异常
- NotFoundException - 资源不存在
- ValidationException - 数据验证失败
- DatabaseException - 数据库错误

#### 4.3 工具函数 (tools.py)
- 字典安全访问
- JSON 解析/序列化
- 分页处理
- 数据清洗

### 5. 中间件 (app/middlewares)

#### 5.1 CORS 中间件 (cors.py)
- 跨域资源共享配置
- 灵活的来源白名单

#### 5.2 请求中间件 (request_mw.py)
- 请求日志记录
- 参数校验装饰器
- 全局异常处理

## 环境配置

### 开发环境 (dev)
- 数据库：SQLite (cmdb_dev.db)
- 调试模式：开启
- 日志级别：DEBUG
- 端口：5000

### 测试环境 (test)
- 数据库：SQLite (cmdb_test.db)
- 调试模式：开启
- 日志级别：DEBUG
- 端口：5001

### 生产环境 (prod)
- 数据库：PostgreSQL
- 调试模式：关闭
- 日志级别：INFO
- 端口：8000

## 实施步骤

### 阶段 1: 基础架构搭建 ✅
- [x] 创建项目目录结构
- [x] 配置管理系统 (config/)
- [x] 数据库核心模块 (db/)
- [x] 工具类和中间件 (utils/, middlewares/)
- [x] 创建 requirements.txt
- [x] 创建 .env 环境变量文件
- [x] 创建 SQLite dev 数据库
- [x] 调试工具验证

### 阶段 2: API 层实现 ⏳
- [ ] 实现分类相关 API
- [ ] 实现模型相关 API
- [ ] 实现实例相关 API
- [ ] 实现关联相关 API
- [ ] API 文档编写

### 阶段 3: 服务层实现 ⏳
- [ ] 分类服务实现
- [ ] 模型服务实现
- [ ] 实例服务实现
- [ ] 关联服务实现

### 阶段 4: SQL 文件整理 ⏳
- [ ] 迁移现有 SQL 到独立文件
- [ ] 规范化 SQL 命名和结构
- [ ] SQL 模板优化

### 阶段 5: 测试和部署 ⏳
- [ ] 单元测试编写
- [ ] 集成测试
- [ ] 部署脚本编写
- [ ] 文档完善

## 技术要点

### 1. 禁用 ORM，只使用 SQLAlchemy 连接池
```python
from sqlalchemy import create_engine, text
# 不使用 declarative_base
# 不定义 Model 类
# 直接使用 text() 执行原生 SQL
```

### 2. sqlglot 方言转译
```python
from sqlglot import transpile
# PostgreSQL -> SQLite
sql = transpile(postgres_sql, read='postgres', write='sqlite')[0]
```

### 3. 参数化查询防注入
```python
# ✅ 推荐
query_one("SELECT * FROM users WHERE id = :id", {"id": user_id})

# ❌ 不推荐
query_one(f"SELECT * FROM users WHERE id = {user_id}")
```

### 4. SQL 文件独立管理
```
app/sql/
├── common/page_limit.sql
├── common/select_models.sql
├── model/select_instances.sql
├── model/insert_instance.sql
└── ...
```

## 注意事项

1. **Python 版本**：固定为 Python 3.9.20
2. **SQLAlchemy 版本**：建议使用 2.0.35+
3. **SQLite**：Python 3 内置，无需额外安装 pysqlite3
4. **数据库驱动**：PostgreSQL 使用 psycopg2-binary，MySQL 使用 pymysql

## 验证测试

### SQLglot 测试
```bash
python3 dev-action/debug_sqlglot.py
```

### SQLAlchemy 测试
```bash
python3 dev-action/debug_sqlalchemy.py
```

## 下一步行动

1. 将现有的 main.py 中的 API 逻辑迁移到 app/api/ 目录
2. 创建对应的 service 层
3. 将所有 SQL 查询提取到 app/sql/ 目录
4. 配置 PostgreSQL 生产环境
5. 编写单元测试
6. 部署上线

---

文档生成时间: 2026-05-29
