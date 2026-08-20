#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bk-cmdb-lite 命令行工具（CLI）

通过 HTTP API 与 cmdb_server_lite 后端交互，目前支持「创建业务（create-biz）」
与「列出业务（list-biz）」两类操作，便于在无需打开 Web UI 的情况下完成业务拓扑初始化。

鉴权：
  - 默认走 /api/v1/auth/login 用账号密码换取 lite_bk_token，
    再以 X-Lite-Token 头携带；
  - 也可用 --token 直接复用已有 token（skipLogin 部署可不传账号密码）。

示例：
  # 创建业务（默认 admin/admin 与 http://127.0.0.1:5000）
  python3 cmdb_cli.py create-biz --biz-name "新业务A"

  # 指定后端 / 账号 / 供应商，并透传可选业务属性
  python3 cmdb_cli.py create-biz \
      --host http://10.0.0.1:5000 \
      --user admin --password admin \
      --biz-name "正式环境2" \
      --supplier 0 \
      --attr bk_biz_maintainer=admin \
      --attr bk_biz_developer=ops

  # 复用 token，跳过登录
  python3 cmdb_cli.py create-biz --token <lite_bk_token> --biz-name "测试业务B"

  # 列出业务
  python3 cmdb_cli.py list-biz

退出码：
  0  成功
  1  鉴权失败（账号密码错误 / 缺 --token 且无账号密码）
  2  参数错误（--attr 格式错 / 缺必要参数）或业务创建被拒绝（重名等）
  3  服务不可达 / 未知错误
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖 requests，请先执行: pip install requests\n")
    sys.exit(3)


DEFAULT_HOST = os.environ.get("CMDB_HOST", "http://127.0.0.1:5000")
DEFAULT_USER = os.environ.get("CMDB_USER", "admin")
DEFAULT_PASS = os.environ.get("CMDB_PASS", "admin")


class CliError(Exception):
    """CLI 层可预期错误，携带退出码。"""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def _login(session: requests.Session, host: str, user: str, password: str,
           timeout: int) -> str:
    """账号密码登录，返回 lite_bk_token。"""
    url = f"{host.rstrip('/')}/api/v1/auth/login"
    try:
        resp = session.post(
            url,
            json={"bk_user_name": user, "bk_password": password},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise CliError(f"登录请求失败（{url}）：{e}", 3)

    body = _parse_body(resp)
    if not body.get("result"):
        raise CliError(
            f"登录失败：{body.get('bk_error_msg') or '未知错误'} "
            f"(code={body.get('bk_error_code')})", 1)
    token = (body.get("data") or {}).get("bk_token")
    if not token:
        raise CliError("登录成功但未返回 bk_token", 1)
    return token


def _parse_body(resp: requests.Response) -> Dict[str, Any]:
    """解析响应体为 dict；非 JSON 时抛出可读错误。"""
    try:
        return resp.json()
    except ValueError:
        raise CliError(
            f"后端返回非 JSON 响应 (HTTP {resp.status_code}): "
            f"{resp.text[:200]}", 3)


def _require_token(args, session: requests.Session, timeout: int) -> str:
    """根据参数获取 token：优先复用 --token，否则登录换取。"""
    if getattr(args, "token", None):
        return args.token
    if not getattr(args, "user", None) or not getattr(args, "password", None):
        raise CliError("未提供 --token，且缺少 --user/--password 用于登录", 1)
    return _login(session, args.host, args.user, args.password, timeout)


def _apply_auth(session: requests.Session, token: str) -> None:
    """以 X-Lite-Token 头携带 token（与前端默认承载方式一致）。"""
    session.headers.update({"X-Lite-Token": token})


def _post_biz(args, session: requests.Session, token: str,
              timeout: int) -> Dict[str, Any]:
    url = f"{args.host.rstrip('/')}/api/v1/topo/biz"
    payload: Dict[str, Any] = {
        "bk_biz_name": args.biz_name,
        "bk_supplier_account": args.supplier,
    }
    for key, value in args.attr:
        payload[key] = value

    try:
        resp = session.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise CliError(f"创建业务请求失败（{url}）：{e}", 3)

    body = _parse_body(resp)
    # 业务层失败（result=false）：统一以退出码 2 表达
    if not body.get("result"):
        msg = body.get("bk_error_msg") or "业务创建被拒绝"
        code = body.get("bk_error_code")
        # 若后端返回 200 + result:false 的 BaseResp（本项目约定）
        raise CliError(f"{msg} (code={code})", 2)
    return body.get("data") or {}


def _list_biz(args, session: requests.Session, token: str,
              timeout: int) -> Dict[str, Any]:
    url = f"{args.host.rstrip('/')}/api/v1/topo/biz"
    params = {"bk_supplier_account": args.supplier}
    try:
        resp = session.get(url, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise CliError(f"获取业务列表失败（{url}）：{e}", 3)
    body = _parse_body(resp)
    if not body.get("result"):
        raise CliError(
            f"{body.get('bk_error_msg') or '获取业务列表失败'} "
            f"(code={body.get('bk_error_code')})", 2)
    return body.get("data") or []


def _parse_attr(pair: str):
    """解析 --attr key=value 形式参数。"""
    if "=" not in pair:
        raise CliError(f"--attr 必须是 key=value 形式，收到：{pair}", 2)
    key, value = pair.split("=", 1)
    key = key.strip()
    if not key:
        raise CliError(f"--attr 的 key 不能为空，收到：{pair}", 2)
    return key, value


def cmd_create_biz(args, session: requests.Session, timeout: int) -> int:
    token = _require_token(args, session, timeout)
    _apply_auth(session, token)
    data = _post_biz(args, session, token, timeout)

    if args.raw:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        biz_id = data.get("bk_biz_id")
        name = data.get("bk_biz_name")
        print(f"✅ 业务创建成功: bk_biz_id={biz_id}, bk_biz_name={name}")
        if args.verbose:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_list_biz(args, session: requests.Session, timeout: int) -> int:
    token = _require_token(args, session, timeout)
    _apply_auth(session, token)
    biz_list = _list_biz(args, session, token, timeout)

    if args.raw:
        print(json.dumps(biz_list, ensure_ascii=False, indent=2))
        return 0

    if not biz_list:
        print("（无业务数据）")
        return 0

    print(f"{'bk_biz_id':<10} {'bk_biz_name':<20} {'default':<8} supplier")
    print("-" * 56)
    for biz in biz_list:
        print(f"{biz.get('bk_biz_id', ''):<10} "
              f"{str(biz.get('bk_biz_name', '')):<20} "
              f"{biz.get('default', 0):<8} "
              f"{biz.get('bk_supplier_account', '0')}")
    return 0


def _common_args() -> argparse.ArgumentParser:
    """连接 / 鉴权 / 输出等公共参数，供主解析器与子命令共享（两种位置均可使用）。"""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"后端地址（默认 {DEFAULT_HOST}）")
    p.add_argument("--user", default=DEFAULT_USER,
                   help=f"登录账号（默认 {DEFAULT_USER}）")
    p.add_argument("--password", default=DEFAULT_PASS,
                   help="登录密码（默认 admin）")
    p.add_argument("--token", default=None,
                   help="直接复用已有 lite_bk_token（跳过登录）")
    p.add_argument("--supplier", default="0",
                   help="供应商账号 bk_supplier_account（默认 0）")
    p.add_argument("--timeout", type=int, default=10,
                   help="请求超时秒数（默认 10）")
    p.add_argument("--raw", action="store_true",
                   help="仅输出原始 JSON 响应")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="成功后额外打印完整业务实例 JSON")
    return p


def build_parser() -> argparse.ArgumentParser:
    common = _common_args()
    parser = argparse.ArgumentParser(
        prog="cmdb_cli",
        description="bk-cmdb-lite 命令行工具（业务创建 / 查询）",
        parents=[common],
    )
    parser.set_defaults(func=None)

    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create-biz", parents=[common], help="创建业务")
    p_create.add_argument("--biz-name", required=True,
                          help="业务名称（bk_biz_name，全局唯一）")
    p_create.add_argument("--attr", action="append", default=[],
                          metavar="key=value",
                          help="透传可选业务属性，可重复，如 "
                               "--attr bk_biz_maintainer=admin")
    p_create.set_defaults(func=cmd_create_biz)

    p_list = sub.add_parser("list-biz", parents=[common], help="列出业务")
    p_list.set_defaults(func=cmd_list_biz)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1

    # 解析 --attr
    if getattr(args, "attr", None):
        try:
            args.attr = [_parse_attr(p) for p in args.attr]
        except CliError as e:
            sys.stderr.write(f"参数错误：{e}\n")
            return e.exit_code
    else:
        args.attr = []

    session = requests.Session()
    try:
        return args.func(args, session, args.timeout)
    except CliError as e:
        sys.stderr.write(f"❌ {e}\n")
        return e.exit_code
    except KeyboardInterrupt:
        sys.stderr.write("已取消\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())
