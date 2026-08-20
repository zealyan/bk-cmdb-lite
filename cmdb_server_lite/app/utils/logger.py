"""
日志初始化模块
"""

import os
import logging
import coloredlogs
from logging.handlers import RotatingFileHandler
from app.config.settings import get_config

def setup_logger(name: str = 'cmdb', level: str = None) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        
    Returns:
        配置好的日志器
    """
    config = get_config()
    log_level = level or config.LOG_LEVEL
    log_dir = config.LOG_DIR
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 文件处理器
    log_file = os.path.join(log_dir, f'{name}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 格式化
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    
    console_formatter = coloredlogs.ColoredFormatter(fmt, datefmt)
    file_formatter = logging.Formatter(fmt, datefmt)
    
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 全局日志器
logger = setup_logger()

def get_logger(name: str = None) -> logging.Logger:
    """获取日志器"""
    if name:
        return logging.getLogger(name)
    return logger
