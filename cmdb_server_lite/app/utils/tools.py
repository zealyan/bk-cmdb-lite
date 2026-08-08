"""
通用工具函数模块
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid
import secrets

# --- ID 生成器：全局唯一、数据库无关 ---
#
# 设计要点：
# 1. 单一全局递增计数器，覆盖 bk_inst_id / bk_biz_id / bk_set_id /
#    bk_module_id / bk_host_id / 实例关联 等所有序列域 → 保证全局唯一
# 2. 起始值 ID_SEQ_START = 10000（5 位），每次 +1，位数随增长自然增加（3~6 位起，逐步递增）
# 3. 不依赖任何数据库特性（无 MAX / 序列 / RETURNING / 自增列），
#    SQLite / PostgreSQL / MySQL 行为完全一致（数据库无关）
# 4. threading.Lock 保证并发安全；状态文件持久化，进程重启后不重复

import threading
import os

ID_SEQ_START = 10000  # 起始值：5 位数，逐步递增

# 序列状态持久化文件（纯文件系统，不依赖任何数据库，保证跨重启全局唯一）
# 与 cmdb_dev.db 同目录，随数据一起管理
_ID_SEQ_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'id_seq.state'
)

_id_seq_lock = threading.Lock()
_id_seq_value = [None]  # 用 list 以便闭包内修改


def _id_seq_load():
    """从状态文件加载当前计数（文件不存在或损坏则返回起始值）"""
    try:
        with open(_ID_SEQ_STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            v = int(state.get('value', ID_SEQ_START))
            return v if v >= ID_SEQ_START else ID_SEQ_START
    except Exception:
        return ID_SEQ_START


def _id_seq_save(value):
    """原子写入当前计数（写临时文件后 rename，避免半写损坏）"""
    try:
        tmp = _ID_SEQ_STATE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'value': value}, f)
        os.replace(tmp, _ID_SEQ_STATE_FILE)
    except Exception:
        # 持久化失败不阻断 ID 生成（仅丢失跨重启唯一性保证）
        pass


def generate_id(scope: str = None, model_id: str = None) -> int:
    """
    生成全局唯一 ID（数据库无关，进程内原子递增 + 文件持久化）

    覆盖 bk_inst_id / biz→bk_biz_id / set→bk_set_id / module→bk_module_id /
    host→bk_host_id 等所有序列域，统一从单一全局计数器取号，保证全局唯一。

    Args:
        scope: 序列域标识（仅语义说明，取值来自全局唯一序列，不受 scope 影响）
        model_id: 模型 ID（兼容旧调用，不影响取值）

    Returns:
        全局唯一整数 ID（从 ID_SEQ_START 起，逐步递增）
    """
    with _id_seq_lock:
        if _id_seq_value[0] is None:
            _id_seq_value[0] = _id_seq_load()
        # 先发号（首条恰好为 ID_SEQ_START），再推进并持久化"下一个待发号"
        val = _id_seq_value[0]
        _id_seq_value[0] += 1
        _id_seq_save(_id_seq_value[0])
    return val


# --- 分组 bk_group_id 生成器：随机全局唯一串（对齐上游 bk-cmdb）---
#
# 上游 src/scene_server/topo_server/logics/model/group.go:334 NewGroupID(isDefault)：
#   - 默认分组固定返回小写 "default"
#   - 非默认分组返回 xid.New().String() —— 随机全局唯一串（20 位 base32 小写）
# 因此 bk_group_id 与记录的整型 id（NextSequence 自增）是两回事：
#   - id             = 记录主键，自增顺序
#   - bk_group_id    = 语义标识，随机唯一、非顺序、不受小写标识符约束
_GROUP_ID_ALPHABET = 'abcdefghijklmnopqrstuvwxyz234567'  # base32 小写，贴近上游 xid


def generate_group_id() -> str:
    """生成分组 bk_group_id：随机全局唯一串（对齐上游 xid.New()）。

    非顺序、不要求小写标识符，与上游 NewGroupID(false) 语义一致。
    用于 --group-auto-create 自动建组、以及分组 API 新建分组。
    """
    return ''.join(secrets.choice(_GROUP_ID_ALPHABET) for _ in range(20))


def safe_get(data: dict, key: str, default: Any = None) -> Any:
    """
    安全获取字典值
    
    Args:
        data: 字典数据
        key: 键名
        default: 默认值
        
    Returns:
        值或默认值
    """
    return data.get(key, default) if isinstance(data, dict) else default

def parse_json(json_str: str, default: Any = None) -> Any:
    """
    安全解析 JSON
    
    Args:
        json_str: JSON 字符串
        default: 解析失败时的默认值
        
    Returns:
        解析后的对象或默认值
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def to_json(data: Any, default: Any = None) -> str:
    """
    安全转换为 JSON 字符串
    
    Args:
        data: 数据对象
        default: 转换失败时的默认值
        
    Returns:
        JSON 字符串或默认值
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return default

def paginate(items: List[Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    分页处理
    
    Args:
        items: 完整列表
        page: 页码 (从 1 开始)
        page_size: 每页数量
        
    Returns:
        分页结果字典
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        'items': items[start:end],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1
    }

def clean_dict(data: Dict[str, Any], remove_none: bool = True, remove_empty: bool = False) -> Dict[str, Any]:
    """
    清理字典
    
    Args:
        data: 字典数据
        remove_none: 是否移除 None 值
        remove_empty: 是否移除空字符串
        
    Returns:
        清理后的字典
    """
    result = {}
    for key, value in data.items():
        if remove_none and value is None:
            continue
        if remove_empty and value == '':
            continue
        result[key] = value
    return result

def get_current_timestamp() -> int:
    """获取当前时间戳"""
    return int(datetime.now().timestamp())

def format_datetime(dt: datetime = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象,默认当前时间
        fmt: 格式字符串
        
    Returns:
        格式化后的字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)
