# CMDB Server Lite 项目说明

## 项目简介

这是一个轻量级的配置管理数据库(CMDB)服务端,基于 Flask 框架构建。

## 技术栈

- **Web 框架**: Flask 2.3.3
- **数据库连接池**: SQLAlchemy 2.0.20 (仅用于连接池,不使用 ORM)
- **数据库方言处理**: sqlglot 19.8.0
- **支持数据库**: SQLite, PostgreSQL, MySQL

## 目录结构

```
cmdb_server_lite/
├── app/                    # 核心源码
│   ├── api/               # API 路由层
│   │   └── v1/            # API v1 版本
│   ├── config/            # 配置中心
│   ├── db/                # 数据库核心层
│   ├── migrate/           # 数据库迁移
│   ├── service/           # 业务逻辑层
│   ├── sql/               # 独立 SQL 文件
│   ├── utils/             # 工具类
│   └── middlewares/       # 中间件
├── logs/                  # 日志目录
├── tests/                 # 测试目录
└── run.py                 # 启动入口
```

## 环境配置

### 开发环境

```bash
export FLASK_ENV=development
python run.py
```

### 生产环境

```bash
export FLASK_ENV=production
python run.py
```

## API 文档

- 健康检查: `GET /api/v1/common/health`
- 统计数据: `GET /api/v1/common/statistics`

## 开发指南

### 添加新的 API

1. 在 `app/api/v1/` 创建蓝图文件
2. 注册蓝图到 Flask 应用
3. 添加对应的 SQL 文件到 `app/sql/`

### 数据库操作

使用 `app.db.executor` 模块:

```python
from app.db.executor import query_all, query_one

# 查询所有
results = query_all("SELECT * FROM table WHERE id = :id", {"id": 1})

# 查询单个
result = query_one("SELECT * FROM table WHERE id = :id", {"id": 1})
```

## 测试

```bash
pytest tests/
```

## License

MIT
