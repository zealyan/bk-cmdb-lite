"""
全局基础配置
定义数据库默认参数、方言枚举等
"""

import os
import secrets as _secrets
import sys as _sys
from enum import Enum

class DatabaseType(Enum):
    """支持的数据库类型"""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgresql'
    MYSQL = 'mysql'
    DUCKDB = 'duckdb'

class DialectType(Enum):
    """sqlglot 支持的方言"""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgres'
    MYSQL = 'mysql'
    DUCKDB = 'duckdb'


def _resolve_secret_key():
    """生产级 SECRET_KEY 解析，保证「任何进程派生方式下全实例密钥一致」。

    历史教训：登录签发的 token 在 /me 校验失败（表现为登录后不跳转），根因是
    SECRET_KEY 在不同进程读到不同值（父进程回退默认、子进程读 .env、平台注入等）。
    硬编码固定值能规避，但不适合生产。本方案改为三级来源：

      ① env SECRET_KEY / CMDB_SECRET_KEY（最高优先）
         —— 生产部署由进程管理器显式注入：uwsgi(gunicorn) 所有 worker 继承同一 env、
            supervisord 经 [program:x] environment= 统一注入 → 全进程天然一致。
      ② 持久化密钥文件 <项目>/instance/secret_key（次优先，自动生成）
         —— 首次启动以 open(..., 'x') 原子创建随机密钥；并发/多 worker 启动时仅一个
            进程写入成功、其余读同一文件 → 多进程、reloader 父子进程天然一致。
      ③ 开发回退值 + 告警日志（兜底）
         —— 仅当 env 与文件都不可用（如只读文件系统）时使用，并输出告警。

    无论 uwsgi/gunicorn/supervisord/Flask reloader 哪种模式派生进程，密钥来源都是
    「同一 env 或同一文件」，杜绝分裂。
    """
    val = os.environ.get('SECRET_KEY') or os.environ.get('CMDB_SECRET_KEY')
    if val:
        return val
    # <项目根>/cmdb_server_lite/instance/secret_key
    instance_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance')
    key_file = os.path.join(instance_dir, 'secret_key')
    try:
        os.makedirs(instance_dir, exist_ok=True)
        if not os.path.exists(key_file):
            try:
                with open(key_file, 'x', encoding='utf-8') as f:
                    f.write(_secrets.token_hex(32))
            except FileExistsError:
                pass  # 并发创建：其他进程已写入，读它的即可
        with open(key_file, 'r', encoding='utf-8') as f:
            stored = f.read().strip()
            if stored:
                return stored
    except OSError as e:
        _sys.stderr.write(
            f'[WARN] SECRET_KEY 密钥文件不可用({e})，回退开发默认值（生产请注入 SECRET_KEY env）\n')
    return 'dev-secret-key-change-in-production'

# 全局基础配置
class BaseConfig:
    """基础配置类"""
    DEBUG = False
    TESTING = False
    ENV = 'base'
    
    # Flask 配置
    # SECRET_KEY 生产级解析：env 优先 → instance/secret_key 持久化文件 → dev 回退，
    # 保证 uwsgi / gunicorn / supervisord / reloader 父子进程全实例同源一致（见 _resolve_secret_key）。
    SECRET_KEY = _resolve_secret_key()
    
    # 数据库配置
    # DATABASE_TYPE 可由环境变量 CMDB_DATABASE_TYPE 覆盖（sqlite/postgresql/mysql），
    # 使同一份代码可指向 SQLite / PostgreSQL / MySQL 三库。
    DATABASE_TYPE = os.environ.get('CMDB_DATABASE_TYPE', DatabaseType.SQLITE.value)
    DATABASE_NAME = 'cmdb.db'
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_NAME)
    # 服务端数据库连接参数（SQLite 不使用；MySQL/PostgreSQL 由 engine.py 拼 URL）
    DATABASE_HOST = os.environ.get('CMDB_DB_HOST', '127.0.0.1')
    DATABASE_PORT = int(os.environ.get('CMDB_DB_PORT', '5432'))
    DATABASE_USER = os.environ.get('CMDB_DB_USER', 'cmdb')
    DATABASE_PASSWORD = os.environ.get('CMDB_DB_PASSWORD', 'cmdb')
    
    # SQLAlchemy 配置 (仅用于连接池)
    SQLALCHEMY_DATABASE_URI = None  # 由 db 模块动态构建
    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_ECHO = False
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    
    # CORS 配置
    CORS_ORIGINS = ['*']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # API 配置
    API_PREFIX = '/api/v1'
    API_VERSION = 'v1'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000

    # ── 内置鉴权配置（最小内置方案，不使用外部 IAM）──
    # skipLogin=True 时后端不强制登录、current_user 回落默认 admin，前端不显示登录页。
    # 部署时设 CMDB_SKIP_LOGIN=false 即开启登录页 + token 强制。
    SKIP_LOGIN = os.environ.get('CMDB_SKIP_LOGIN', 'true').lower() == 'true'
    # ── 认证载荷（token 承载方式）开关 ──
    # Authorization: Bearer 承载开关（T/F，【默认 F=关闭】）。
    # 默认关闭原因：agentos 分享链接网关在转发请求时会注入/覆盖
    #   Authorization: Bearer <平台 token>（非本 CMDB 后端签发）。一旦后端优先采用该头做
    #   校验，真实 token 会被遮蔽 → 登录态被误判为「未登录」（表现为「登录后不跳转首页」）。
    #   默认关闭 Bearer，让请求改走 Cookie / X-Lite-Token 自定义头承载，规避网关注入污染。
    #   仅在确认部署链路不会污染 Authorization 头时（如本地直连、可信反向代理）才置 T 开启。
    AUTH_BEARER = os.environ.get('CMDB_AUTH_BEARER', 'false').lower() == 'true'
    # URL query（?lite_bk_token=）兜底承载开关（T/F，【默认 F=关闭】）。
    # 默认关闭原因：token 出现在 URL query 会被写入代理访问日志、浏览器地址栏历史、Referer 头，
    #   存在凭据泄露面。当前已有更安全的 Cookie / X-Lite-Token 头承载，query 仅作为
    #   「无法设置自定义头（CLI / 部分网关白名单之外的客户端）」场景的最后兜底。
    #   默认关闭以降低泄露面；确有必要时置 T。
    AUTH_TOKEN_QUERY = os.environ.get('CMDB_AUTH_TOKEN_QUERY', 'false').lower() == 'true'
    # 认证载荷（token）来源解析顺序。current_user_payload() 按本顺序逐个尝试，取
    #   「第一个能通过签名校验」的载荷（first-valid-wins）：顺序只决定优先级与尝试顺序，
    #   不影响正确性（某来源被污染/剥离时自动落到下一个有效来源）。
    #   各元素含义：
    #     COOKIE       —— 浏览器会话承载（lite_bk_token cookie，setToken 写入；本 lite 自定义名）
    #     BEARER       —— Authorization: Bearer <token>（受 AUTH_BEARER 开关控制）
    #     X_LITE_TOKEN —— 自定义头 X-Lite-Token（agentos 网关对 X- 前缀头透传，
    #                   用于无 Cookie / Bearer 被污染场景的可靠承载；非上游内置，为本项目自定义）
    #     QUERY        —— ?lite_bk_token=（受 AUTH_TOKEN_QUERY 开关控制，网关不剥 query；本 lite 自定义名）
    #   默认顺序仅保留 COOKIE + X_LITE_TOKEN 两种来源（BEARER / QUERY 不纳入默认顺序），
    #   契合「仅用 COOKIE + X-Lite-Token」的部署约束；如需启用可经
    #   CMDB_AUTH_PAYLOAD_ORDER=COOKIE,X_LITE_TOKEN,BEARER,QUERY 覆盖。
    AUTH_PAYLOAD_ORDER = [s.strip().upper() for s in
        os.environ.get('CMDB_AUTH_PAYLOAD_ORDER',
                       'COOKIE,X_LITE_TOKEN').split(',') if s.strip()]
    # token 有效期（秒），用 itsdangerous.TimedSerializer.max_age 实现
    TOKEN_MAX_AGE = int(os.environ.get('CMDB_TOKEN_MAX_AGE', '3600'))
    # 无身份时的回落用户 / 供应商（dev / skipLogin 场景）
    DEFAULT_USER = os.environ.get('CMDB_DEFAULT_USER', 'admin')
    DEFAULT_SUPPLIER = os.environ.get('CMDB_DEFAULT_SUPPLIER', '0')
    # 启动时自动创建的初始管理员（bk_role=1 超管）
    BOOTSTRAP_ADMIN_USER = os.environ.get('CMDB_ADMIN_USER', 'admin')
    BOOTSTRAP_ADMIN_PASS = os.environ.get('CMDB_ADMIN_PASS', 'admin')
    # 身份相关错误码（对齐上游：result:false + bk_error_code，HTTP 仍 200）
    AUTH_ERR_UNAUTHORIZED = 1302100   # 未登录 / 登录失效
    AUTH_ERR_BAD_CREDENTIAL = 1302101 # 用户名或密码错误
    AUTH_ERR_NO_PERMISSION = 1302102  # 无操作权限（CCNoPermission）
    AUTH_ERR_NO_PERMISSION_MSG = '无操作权限'  # 无权限统一提示文案（全站唯一）

    # ── RBAC 总开关（模式 B：内置轻量权限）──
    # ENABLE_AUTH=False（默认）时全局短路放行，行为与现状完全一致（零回归）。
    # 设为 true 开启内置 RBAC：supplier 隔离 + 创建者自管 + 管理员全权 + 模型级策略。
    ENABLE_AUTH = os.environ.get('CMDB_ENABLE_AUTH', 'false').lower() == 'true'

# 开发环境配置
class DevelopmentConfig(BaseConfig):
    ENV = 'development'
    DEBUG = True
    # 开发默认 SQLite；可用 CMDB_DATABASE_TYPE 切换到 postgresql/mysql 做本地三库验证
    DATABASE_TYPE = os.environ.get('CMDB_DATABASE_TYPE', DatabaseType.SQLITE.value)
    DATABASE_NAME = 'cmdb_dev.db'
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_ECHO = True

# 测试环境配置
class TestingConfig(BaseConfig):
    ENV = 'testing'
    TESTING = True
    DATABASE_TYPE = DatabaseType.SQLITE.value
    DATABASE_NAME = 'cmdb_test.db'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_NAME}"

# 生产环境配置
class ProductionConfig(BaseConfig):
    ENV = 'production'
    DEBUG = False
    DATABASE_TYPE = DatabaseType.POSTGRESQL.value
    LOG_LEVEL = 'WARNING'
    SQLALCHEMY_ECHO = False

# 配置字典
config_by_env = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """获取配置类"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config_by_env.get(env, config_by_env['default'])
