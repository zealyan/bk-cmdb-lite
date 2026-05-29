
#!/usr/bin/env python3
"""独立运行迁移脚本，避免导入整个应用的依赖问题"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 直接导入并运行迁移模块
from app.migrate.migrate import DatabaseMigrator
from app.config.settings import get_settings


if __name__ == "__main__":
    settings = get_settings()
    migrator = DatabaseMigrator(settings.DATABASE_URI)
    migrator.migrate()

