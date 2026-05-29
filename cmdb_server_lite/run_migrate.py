#!/usr/bin/env python3
"""运行数据库迁移"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.migrate.migrate import DatabaseMigrator

if __name__ == "__main__":
    migrator = DatabaseMigrator()
    migrator.migrate()
