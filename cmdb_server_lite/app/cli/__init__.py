"""CMDB-Lite CLI 包。

按 docs/CLI工具设计文档.md 落地。公共依赖拆分：
- safety:   标识符安全校验（C1）唯一强制入口
- db:       复用 app.db.executor 的连接池/事务，支持 --db 覆盖
- io_utils: RFC4180 CSV 读写、拒绝汇、运行清单、类型归一（ETL 纪律）
- cmdb:     主入口与各子命令
"""
