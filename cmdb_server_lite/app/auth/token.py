"""
Token 工具：itsdangerous.TimedSerializer 签名令牌（自带有效期）

- 不引入 JWT：itsdangerous 已随 Flask 安装，语义等同（签名 + 携带身份 + 可过期）。
- payload 形状对齐上游 bk_token：{bk_user_name, bk_supplier_account, bk_role}
"""
from itsdangerous import TimedSerializer, SignatureExpired, BadSignature
from app.config.settings import get_config


def _serializer():
    return TimedSerializer(get_config().SECRET_KEY)


def make_token(payload, max_age=None):
    """签发令牌；有效期由 load_token 的 max_age 校验（TimedSerializer 自带时间戳）"""
    return _serializer().dumps(payload)


def load_token(token, max_age=None):
    """校验并解析令牌；过期/非法返回 None"""
    cfg = get_config()
    try:
        return _serializer().loads(token, max_age=max_age or cfg.TOKEN_MAX_AGE)
    except (SignatureExpired, BadSignature):
        return None
