"""
通用工具函数模块
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid

# --- ID 生成器：按序列域递增 ---
#
# 设计要点：
# 1. 每类 ID 维护独立的 DB 递增序列（MAX+1），互不干扰
# 2. 起始值 ID_SEQ_START = 10000（5 位），逐步 +1 递增
# 3. 无参调用 generate_id() 时，返回进程内自增序列（兼容旧关联 ID 等场景）
# 4. 指定 scope 时，从对应表/列取 MAX+1，保证 DB 落库唯一

ID_SEQ_START = 10000  # 起始值：5 位数，逐步递增

# 各序列域 → (表名, ID 列名) 映射
# None 表示该 scope 使用进程内自增（不查 DB），用于无固定表的场景
_ID_SCOPE_TABLE_MAP = {
    'bk_biz_id':    ('cc_ApplicationBase', 'bk_biz_id'),
    'bk_set_id':    ('cc_SetBase',         'bk_set_id'),
    'bk_module_id': ('cc_ModuleBase',      'bk_module_id'),
    'bk_host_id':   ('cc_HostBase',        'bk_host_id'),
    'bk_inst_id':   None,  # 自定义模型分表，需 model_id 动态定位
    'inst_assoc':   None,  # 实例关联分表，使用进程内自增兜底
}

# 进程内自增计数器（用于无固定表的 scope，如 inst_assoc）
# 起始值与 DB 种子数据错开，避免冲突
_proc_seq_counter = {'_default': ID_SEQ_START}


def generate_id(scope: str = None, model_id: str = None) -> int:
    """
    生成唯一 ID（按序列域递增）

    策略：
    - scope 为 None：返回进程内自增整数（从 ID_SEQ_START 起），兼容无表场景
    - scope 指定且映射到固定表：SELECT MAX(列) + 1，下限 ID_SEQ_START
    - scope='bk_inst_id' 且 model_id 指定：从对应分表取 MAX(bk_inst_id)+1

    Args:
        scope: 序列域，可选值见 _ID_SCOPE_TABLE_MAP 的 key
        model_id: 模型 ID（仅 scope='bk_inst_id' 时需要）

    Returns:
        唯一整数 ID（从 ID_SEQ_START 起，逐步递增）
    """
    global _proc_seq_counter

    # 无 scope：进程内自增兜底
    if scope is None:
        val = _proc_seq_counter.get('_default', ID_SEQ_START)
        _proc_seq_counter['_default'] = val + 1
        return val

    table_info = _ID_SCOPE_TABLE_MAP.get(scope)

    # scope 不在映射表 或 映射为 None：进程内自增
    if table_info is None:
        key = scope or '_default'
        val = _proc_seq_counter.get(key, ID_SEQ_START)
        _proc_seq_counter[key] = val + 1
        return val

    table_name, id_column = table_info

    # 自定义模型实例表：动态表名
    if scope == 'bk_inst_id' and model_id:
        table_name = f"cc_ObjectBase_0_pub_{model_id}"

    # 从 DB 取 MAX(id)+1，下限 ID_SEQ_START
    try:
        from app.db.executor import query_one
        row = query_one(
            f'SELECT MAX("{id_column}") as max_id FROM "{table_name}"',
            {}
        )
        current_max = (row['max_id'] if row and row['max_id'] else 0)
    except Exception:
        current_max = 0

    next_id = max(current_max + 1, ID_SEQ_START)
    return next_id

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
