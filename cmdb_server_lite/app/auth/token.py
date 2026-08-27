"""
Token 工具：itsdangerous.URLSafeTimedSerializer 签名令牌（自带有效期）

- 不引入 JWT：itsdangerous 已随 Flask 安装，语义等同（签名 + 携带身份 + 可过期）。
- payload 形状对齐上游 bk_token：{bk_user_name, bk_supplier_account, bk_role}
- 序列化器选用 URLSafeTimedSerializer（而非默认 TimedSerializer）：
  默认 TimedSerializer 用 json 做载荷序列化，会把 payload 原文嵌进 token 的
  value 第一段（形如 {"bk_user_name":"admin",...}.<ts>.<sig>），导致认证 KV
  的 value 里出现 JSON 字符（{ } "），与上游「bk_token 为不透明会话令牌」
  的扁平标量约定不符。URLSafeTimedSerializer 对载荷做 base64，value 完全不
  含 JSON 字符，且是 TimedSerializer 子类，max_age / 载荷语义完全一致。
"""
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.config.settings import get_config


def _serializer():
    return URLSafeTimedSerializer(get_config().SECRET_KEY)


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
