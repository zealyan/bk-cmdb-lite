# bk-cmdb-lite

蓝鲸配置平台（bk-cmdb）v3.10.x 本地开发环境的最小化复刻（Go 后端 → Python 改写，Vue 前端保持对齐）。

## 目录

- `bk-cmdb/`：原项目上游源码参考（只读）
- `cmdb_server_lite/`：LITE 后端（FastAPI/Flask，SQLite/MySQL/PostgreSQL 三库通用）
- `cmdb_ui_lite/`：LITE 前端（Vue CLI，对齐原项目资源/业务拓扑视图）

## 快速开始

```bash
# 后端（默认 SQLite，端口 5000）
cd cmdb_server_lite && python3 run.py

# 前端（端口 3000，需先 build）
cd cmdb_ui_lite && npx vue-cli-service serve
```

## 文档

- **[CLI 使用手册](cmdb_server_lite/CLI使用手册.md)**：命令行工具全命令组说明，含本次新增的通用模型关联 `association`（非主线，`create`/`delete`/`list`，幂等 + 级联清理）。
- [BUG 修复报告](BUG_FIX_REPORT.md)

## 已实现能力

- 资源管理（模型 / 属性 / 实例 / 唯一性校验）
- 业务拓扑（主线 `bk_mainline`：biz-set-module-host）
- **通用模型关联**（非主线）：`cmdb association` + `/create|delete/objectassociation` API
- 主机详情、收藏菜单、面包屑竞态修复
