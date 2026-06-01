"""
自定义业务异常模块
"""

class APIException(Exception):
    """API 异常基类"""
    
    def __init__(self, message: str, status_code: int = 400, payload: dict = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self):
        return {
            'error': self.message,
            'status_code': self.status_code,
            **self.payload
        }

class NotFoundException(APIException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "Resource not found", resource: str = None):
        super().__init__(message, status_code=404)
        if resource:
            self.payload = {'resource': resource}

class ValidationException(APIException):
    """数据验证异常"""
    
    def __init__(self, message: str = "Validation failed", errors: list = None):
        super().__init__(message, status_code=400)
        self.payload = {'errors': errors or []}

class DatabaseException(APIException):
    """数据库异常"""
    
    def __init__(self, message: str = "Database error", original_error: Exception = None):
        super().__init__(message, status_code=500)
        if original_error:
            self.payload = {'original_error': str(original_error)}

class UnauthorizedException(APIException):
    """未授权异常"""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)

class ForbiddenException(APIException):
    """禁止访问异常"""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)
