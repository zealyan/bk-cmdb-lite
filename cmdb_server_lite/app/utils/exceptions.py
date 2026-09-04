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
    CCErrTopoHasChildNode = 1101033
    # ── 服务分类（ServiceCategory）专用错误码 ──
    CCErrServiceCategoryHasChildNode = 1199020      # 一级分类下存在二级分类，禁止删除
    CCErrServiceCategoryBuiltInForbidden = 1199021  # 内置分类禁止修改/删除
    # ── 关联类型（AssociationKind / cc_AsstDes）专用错误码 ──
    # 对齐上游语义（上游为 CCErrorTopoDeletePredefinedAssociationKind /
    # CCErrorTopoAssociationKindHasBeenUsed，见 src/common/errInfo.go），
    # lite 沿用自有 1199xxx 号段，与服务分类的自定义码风格一致。
    CCErrAssociationKindPreForbidden = 1199022      # 预置关联类型（ispre）禁止修改/删除
    CCErrAssociationKindHasBeenUsed = 1199023       # 关联类型已被模型关联引用，禁止删除
    # ── HTTP 状态 → 业务错误码（HTTPException 兜底统一映射，公共层引用）──
    CCErrCommHTTPError = 1199000         # 通用 HTTP 异常兜底（未单列状态码）
    CCErrCommUnauthorized = 1199001      # 401 未认证
    CCErrCommForbidden = 1199002         # 403 无权限访问
    CCErrCommMethodNotAllowed = 1199003  # 405 请求方法不允许
    CCErrCommRequestTimeout = 1199004    # 408 请求超时
    CCErrCommPayloadTooLarge = 1199005   # 413 请求体过大
    CCErrCommUnsupportedMedia = 1199007  # 415 不支持的媒体类型
    CCErrCommTooManyRequests = 1199008   # 429 请求过于频繁
    CCErrCommRedirect = 1199009          # 3xx 重定向


# HTTP 状态码 → (bk_error_code, bk_error_msg) 公共映射。
# Flask 未单列注册的 HTTP 异常（405/400/408/413/415/429/3xx 等）统一走这里，
# 保证所有响应都遵守 BaseResp（result + bk_error_code + bk_error_msg）结构。
HTTP_STATUS_ERROR_META = {
    400: (CCErrorCode.CCErrCommParamsInvalid, '请求参数有误，请检查后重试'),
    401: (CCErrorCode.CCErrCommUnauthorized, '未认证或登录已失效，请重新登录'),
    403: (CCErrorCode.CCErrCommForbidden, '没有访问该资源的权限'),
    404: (CCErrorCode.CCErrCommNotFound, '请求路径不存在'),
    405: (CCErrorCode.CCErrCommMethodNotAllowed, '请求方式不被支持'),
    408: (CCErrorCode.CCErrCommRequestTimeout, '请求超时，请稍后重试'),
    413: (CCErrorCode.CCErrCommPayloadTooLarge, '请求体过大，请精简后重试'),
    415: (CCErrorCode.CCErrCommUnsupportedMedia, '不支持的媒体类型'),
    429: (CCErrorCode.CCErrCommTooManyRequests, '请求过于频繁，请稍后重试'),
}


def http_error_meta(status_code: int):
    """将 HTTP 状态码映射为 (bk_error_code, bk_error_msg)，公共层统一引用。

    - 5xx → 服务器内部错误（1199999）
    - 3xx → 重定向（1199009）
    - 已单列的 4xx → 对应可读文案
    - 其余状态 → 通用 HTTP 异常兜底（1199000）
    """
    if status_code >= 500:
        return CCErrorCode.CCErrCommInternalServerError, '服务器内部错误'
    if 300 <= status_code < 400:
        return CCErrorCode.CCErrCommRedirect, '请求被重定向，请刷新后重试'
    return HTTP_STATUS_ERROR_META.get(
        status_code, (CCErrorCode.CCErrCommHTTPError, '请求失败，请稍后重试'))


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
