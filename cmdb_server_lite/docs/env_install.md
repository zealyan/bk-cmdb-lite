# CMDB Server Lite 环境安装文档

## Python 版本

- **Python 版本**: Python 3.9.20

## 相关依赖和版本

### 依赖清单

```txt
# Flask Web Framework
Flask==2.3.3
Werkzeug==2.3.7
Flask-CORS==6.0.2

# Database Connection Pool & SQL Execution
SQLAlchemy>=2.0.35

# Native DB drivers
psycopg2-binary==2.9.7  # PostgreSQL
pymysql==1.1.0  # MySQL
# SQLite: 使用 Python 内置 sqlite3，无需额外安装

# Multi-Database Dialect Processing
sqlglot==19.8.0

# Environment Variables
python-dotenv==1.0.0

# Logging
coloredlogs==15.0.1

# Development & Testing
pytest==7.4.2
pytest-flask==1.2.0

# Utilities
click==8.1.7
```

## 中国镜像源配置

### 1. pip 镜像源配置

#### 临时使用（单次安装）

```bash
# 使用清华源
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用阿里云源
pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# 使用中科大源
pip3 install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple

# 使用豆瓣源
pip3 install -r requirements.txt -i https://pypi.douban.com/simple
```

#### 永久配置（推荐）

**Linux/macOS**:

```bash
# 方法一：使用命令配置
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 方法二：创建配置文件
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

**Windows**:

```cmd
# 创建 pip 配置文件
mkdir %USERPROFILE%\pip
type nul > %USERPROFILE%\pip\pip.ini

# 编辑 pip.ini，添加以下内容:
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
```

### 2. Pyenv 镜像源配置

```bash
# 配置 Pyenv 使用中国镜像（加速 Python 安装）
export PYENV_BUILD_MIRROR_URL=https://npmmirror.com/mirrors/python-build
export PYTHON_BUILD_MIRROR_URL=https://npmmirror.com/mirrors/python

# 安装 Python
pyenv install 3.9.20
```

## 完整安装步骤

### 1. 安装 Python

#### 使用 Pyenv 安装（推荐）

```bash
# 安装 pyenv（如果未安装）
git clone https://gitee.com/mirrors/pyenv.git ~/.pyenv

# 配置环境变量（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
source ~/.bashrc

# 安装 Python 3.9.20
pyenv install 3.9.20

# 设置项目使用的 Python 版本
cd /workspace/cmdb_server_lite
pyenv local 3.9.20
python --version  # 确认是 Python 3.9.20
```

### 2. 创建虚拟环境

```bash
cd /workspace/cmdb_server_lite

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境（Linux/macOS）
source venv/bin/activate

# 激活虚拟环境（Windows）
# venv\Scripts\activate

# 升级 pip
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 安装依赖

```bash
# 确保在虚拟环境中 (venv) 提示符出现

# 使用清华源安装依赖（推荐）
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用配置好的镜像源
pip3 install -r requirements.txt
```

### 4. 验证安装

```bash
# 验证 Python 版本
python --version
# 输出: Python 3.9.20

# 验证依赖安装
pip3 list

# 验证数据库连接
python3 -c "
import sqlite3
conn = sqlite3.connect('cmdb_dev.db')
cursor = conn.cursor()
cursor.execute('SELECT 1')
print('✅ 数据库连接成功')
conn.close()
"
```

## 目录结构

```
/workspace/cmdb_server_lite/
├── venv/                     # 虚拟环境目录 (新)
├── app/                      # 核心源码
├── dev-action/               # 调试工具
├── docs/                     # 文档目录
│   └── env_install.md        # 本文档 (新)
├── logs/                     # 日志目录
├── tests/                    # 测试目录
├── cmdb_dev.db               # SQLite 开发数据库
├── .env                      # 开发环境变量
├── requirements.txt          # 依赖清单
└── run.py                    # 启动入口
```

## 快速开始

### 激活虚拟环境并运行

```bash
cd /workspace/cmdb_server_lite

# 激活虚拟环境
source venv/bin/activate

# 启动应用
python run.py

# 访问健康检查
curl http://localhost:5000/api/v1/common/health
```

### 运行测试

```bash
# 运行 pytest 测试
python -m pytest tests/ -v

# 运行调试工具
python dev-action/debug_sqlalchemy.py
python dev-action/debug_sqlglot.py
```

## 常见问题

### Q1: 依赖下载缓慢怎么办？

**A**: 配置中国镜像源后再安装，见上文"中国镜像源配置"章节。

### Q2: 如何切换回官方源？

```bash
# 临时使用官方源
pip3 install -r requirements.txt -i https://pypi.org/simple

# 永久配置
pip3 config set global.index-url https://pypi.org/simple
```

### Q3: 如何验证虚拟环境是否激活？

```bash
# 查看 Python 路径
which python
# 应该指向: /workspace/cmdb_server_lite/venv/bin/python

# 或查看 pip 路径
which pip
# 应该指向: /workspace/cmdb_server_lite/venv/bin/pip
```

### Q4: Python 版本要求是什么？

**A**: 本项目固定使用 Python 3.9.20。

## 数据库连接测试

### SQLite 测试

```python
import sqlite3

conn = sqlite3.connect('cmdb_dev.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)')
conn.commit()
conn.close()
print('✅ SQLite 连接成功')
```

### SQLAlchemy 测试

```python
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///cmdb_dev.db')

with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print(f'✅ SQLAlchemy 查询结果: {result.fetchone()}')
```

---

**文档创建日期**: 2026-05-29
