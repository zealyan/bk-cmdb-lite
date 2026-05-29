#!/usr/bin/env python3
"""
独立运行数据库迁移的脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.config.settings import get_config
from app.db.engine import init_db
from app.migrate.migrate import DatabaseMigrator

if __name__ == "__main__":
    # 初始化数据库
    config = get_config()
    init_db(config)
    
    # 执行迁移
    migrator = DatabaseMigrator(config)
    migrator.migrate()
