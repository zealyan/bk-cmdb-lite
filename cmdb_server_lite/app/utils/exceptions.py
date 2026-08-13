"""
自定义业务异常模块
与原项目蓝鲸CMDB错误响应格式保持一致

BaseResp 格式:
{
    "result": false,
    "bk_error_code": 1199014,
    "bk_error_msg": "错误信息"
}
"""

# 错误码定义（与原项目保持一致）
class CCErrorCode:
    """蓝鲸CMDB错误码"""
    CCSuccess = 0
    CCErrCommDuplicateItem = 1199014
    CCErrTopoInstCreateFailed = 1101000
    CCErrTopoInstUpdateFailed = 1101002
    CCErrCommParamsInvalid = 1199006
    CCErrCommNotFound = 1199019
    CCErrCommInternalServerError = 1199999
    CCErrTopoHasHostCheckFailed = 1101030
    CCErrorTopoForbiddenDeleteBuiltInBiz = 1101031
    CCErrorTopoInstHasAssociation = 1101032


class APIException(Exception):
    """API 异常基类 - 输出与原项目 BaseResp 格式一致"""

    def __init__(self, message: str, status_code: int = 200, error_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or CCErrorCode.CCErrCommParamsInvalid

    def to_dict(self):
        return {
            'result': False,
            'bk_error_code': self.error_code,
            'bk_error_msg': self.message
        }


class NotFoundException(APIException):
    """资源不存在异常 - 返回 200 + BaseResp 格式，与原项目一致"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=200, error_code=CCErrorCode.CCErrCommNotFound)


class ValidationException(APIException):
    """数据验证异常（唯一性校验等）"""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=400, error_code=CCErrorCode.CCErrCommDuplicateItem)


class DatabaseException(APIException):
    """数据库异常"""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, status_code=500, error_code=CCErrorCode.CCErrCommInternalServerError)


class UnauthorizedException(APIException):
    """未授权异常"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, error_code=CCErrorCode.CCErrCommInternalServerError)


class ForbiddenException(APIException):
    """禁止访问异常"""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, error_code=CCErrorCode.CCErrCommInternalServerError)
