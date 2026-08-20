"""
请求日志/入参校验中间件
"""

from flask import request, g
from functools import wraps
from app.utils.logger import get_logger
from app.utils.tools import safe_get
import time

logger = get_logger('middleware')

def log_request():
    """记录请求日志"""
    g.start_time = time.time()
    
    logger.info(f"[REQUEST] {request.method} {request.path}")
    logger.debug(f"[HEADERS] {dict(request.headers)}")
    
    if request.is_json:
        logger.debug(f"[BODY] {request.get_json()}")
    elif request.form:
        logger.debug(f"[FORM] {dict(request.form)}")

def log_response(response):
    """记录响应日志"""
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"[RESPONSE] {request.method} {request.path} - {response.status_code} - {elapsed:.3f}s")
    
    return response

def validate_json_params(*required_params):
    """
    验证 JSON 请求参数装饰器
    
    Args:
        *required_params: 必填参数列表
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return {'error': 'Content-Type must be application/json'}, 400
            
            data = request.get_json() or {}
            missing = [p for p in required_params if not safe_get(data, p)]
            
            if missing:
                return {
                    'error': 'Missing required parameters',
                    'missing': missing
                }, 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(f):
    """
    全局异常处理装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ERROR] {str(e)}", exc_info=True)
            return {
                'error': 'Internal server error',
                'message': str(e)
            }, 500
    return decorated_function
