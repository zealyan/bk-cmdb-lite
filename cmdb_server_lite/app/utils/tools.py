"""
通用工具函数模块
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

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
