# -*- coding: utf-8 -*-
"""鉴权管理 CLI（app/cli/auth_cmd.py）。

按 docs/CLI工具设计文档.md 的约定落地，复用：
- app.db.auth 公共数据层（多方言 + 项目 db 框架，与后端 API 共用同一套 SQL/方言逻辑）
- 全局选项 --db / --env / --dry-run / --json（来自 cmdb.py 的 common 父解析器）

命令组（cmdb auth ...）：
  cmdb auth user create    创建用户
  cmdb auth user update    修改用户密码
  cmdb auth user list      列出全部用户
  cmdb auth policy grant   授予单/多动作策略（--model 指定 obj_id；--res-type 指定资源类型，省略则 modelInstance）
  cmdb auth policy revoke  撤销策略（--model + --res-type + --action，动作可逗号分隔）
  cmdb auth policy list    列出策略（可按 --user / --model / --res-type / --action 过滤）
  cmdb auth policy grant-scenario  按场景批量授权（readonly / readwrite / update-only / model-owner / topo-admin / host-transfer；topo-admin/host-transfer 可加 --biz-id 限定业务）
  cmdb auth action list    列出全部合法 action（逗号分隔，供 --action 参考）
  cmdb auth res-type list  列出全部合法 res_type（含说明与可用动作，供 --res-type 参考）
  cmdb auth model list     列出全部模型 ID（逗号分隔，供 --models 参考）

退出码沿用 cmdb.py：0 成功 / 2 参数错误 / 4 已存在 / 1 通用错误。
"""

import argparse

from app.cli.errors import CliError, EXIT_OK, EXIT_PARAM, EXIT_EXISTS, EXIT_GENERAL
from app.cli.cmdb import emit_result
from app.db.auth import (
    ROLE_ADMIN, ROLE_NORMAL,
    list_users as db_list_users,
    create_user as db_create_user,
    exists_user as db_exists_user,
    update_user_password as db_update_user_password,
    list_policies as db_list_policies,
    grant_policy as db_grant_policy,
    revoke_policy as db_revoke_policy,
    resolve_scenario as db_resolve_scenario,
    grant_batch as db_grant_batch,
    list_model_ids as db_list_model_ids,
    SCENARIOS, VALID_ACTIONS, VALID_RES_TYPES, RES_TYPE_DESCRIPTIONS,
    RES_TYPE_MODEL_INSTANCE, EFFECT_ALLOW,
    RES_TYPE_BIZ_TOPOLOGY, RES_TYPE_HOST_INSTANCE,
    default_supplier,
)


def _split_csv(val):
    if not val:
        return None
    return [v.strip() for v in str(val).split(',') if v.strip()]


def _fmt_obj(obj_id):
    return obj_id if obj_id else '全部模型(NULL)'


# 资源类型 → 当前被网关实际产出的动作（与 app/auth/parser.py 对齐，用于 res-type list 展示）
_RES_TYPE_ACTIONS = {
    'modelInstance': ['create', 'update', 'delete', 'find'],
    'biz_topology':  ['create', 'update', 'delete'],
    'hostInstance':  ['transfer'],
    'business':      [],   # reserved：解析器暂未产出
    'model':         [],   # reserved：解析器暂未产出
}


def _actions_for_res_type(res_type):
    return _RES_TYPE_ACTIONS.get(res_type, [])


def _emit(summary, json_out):
    emit_result(summary, json_out)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------
def cmd_auth_user_create(args):
    name = (args.name or '').strip()
    if not name:
        raise CliError(EXIT_PARAM, '用户名不能为空（--name 必填）', 'create_user')
    if len(args.password) < 6:
        raise CliError(EXIT_PARAM, '密码长度至少 6 位', 'create_user')
    if args.role not in (ROLE_ADMIN, ROLE_NORMAL):
        raise CliError(EXIT_PARAM, f'非法角色: {args.role}（仅 1=超管 / 2=普通用户）', 'create_user')
    supplier = args.supplier or default_supplier()

    if args.dry_run:
        _emit({
            'dry_run': True,
            'action': 'create_user',
            'user': name, 'role': args.role, 'supplier': supplier,
            'human': f"[dry-run] 将创建用户 {name}（bk_role={args.role}, supplier={supplier}）",
        }, args.json)
        return EXIT_OK

    if db_exists_user(name):
        raise CliError(EXIT_EXISTS, f'用户已存在: {name}', 'create_user')
    user = db_create_user(name=name, password=args.password, role=args.role, supplier=supplier)
    safe = {k: v for k, v in user.items() if k != 'bk_password'}
    _emit({**safe, 'human': f"用户 {name} 创建成功（bk_role={args.role}）"}, args.json)
    return EXIT_OK


def cmd_auth_user_update(args):
    name = (args.name or '').strip()
    if not name:
        raise CliError(EXIT_PARAM, '用户名不能为空（--name 必填）', 'update_user')
    if not args.password:
        raise CliError(EXIT_PARAM, '新密码不能为空（--password 必填）', 'update_user')
    supplier = args.supplier or default_supplier()

    if args.dry_run:
        _emit({
            'dry_run': True, 'action': 'update_user', 'user': name,
            'supplier': supplier,
            'human': f"[dry-run] 将修改用户 {name} 的密码（supplier={supplier}）",
        }, args.json)
        return EXIT_OK

    if not db_exists_user(name):
        raise CliError(EXIT_PARAM, f'用户不存在: {name}', 'update_user')
    user = db_update_user_password(name=name, password=args.password, supplier=supplier)
    safe = {k: v for k, v in user.items() if k != 'bk_password'}
    _emit({**safe, 'human': f"用户 {name} 密码已更新（bk_role={safe.get('bk_role')}）"}, args.json)
    return EXIT_OK


def cmd_auth_user_list(args):
    users = db_list_users()
    safe = [{k: v for k, v in u.items() if k != 'bk_password'} for u in users]
    _emit({
        'count': len(safe),
        'users': safe,
        'human': '\n'.join(f"  {u['bk_user_name']}\trole={u['bk_role']}\tsupplier={u['bk_supplier_account']}" for u in safe)
    }, args.json)
    return EXIT_OK


def cmd_auth_policy_grant(args):
    principal = (args.user or '').strip()
    if not principal:
        raise CliError(EXIT_PARAM, '用户名必填（--user）', 'policy_grant')
    if not db_exists_user(principal):
        raise CliError(EXIT_PARAM, f'用户不存在: {principal}', 'policy_grant')
    actions = _split_csv(args.action)
    if not actions:
        raise CliError(EXIT_PARAM, '动作必填（--action，可逗号分隔：create,update,delete,find,transfer）', 'policy_grant')
    bad = [a for a in actions if a not in VALID_ACTIONS]
    if bad:
        raise CliError(EXIT_PARAM, f'非法动作: {bad}（仅 {VALID_ACTIONS}）', 'policy_grant')
    supplier = args.supplier or default_supplier()
    res_type = args.res_type or RES_TYPE_MODEL_INSTANCE
    if res_type not in VALID_RES_TYPES:
        raise CliError(EXIT_PARAM, f'非法资源类型: {res_type}（仅 {VALID_RES_TYPES}）', 'policy_grant')
    obj_id = args.model or None  # 省略 --model → 类级（全部模型/null）；拓扑/转移用 --model 指定 obj_id
    biz_id = args.biz_id or None  # 省略 → 全部业务（类级）；拓扑 per-biz 授权填业务 ID

    plan = [{'supplier': supplier, 'principal': principal, 'res_type': res_type,
             'obj_id': obj_id, 'action': a, 'business_id': biz_id, 'effect': EFFECT_ALLOW}
            for a in actions]

    if args.dry_run:
        _emit({
            'dry_run': True, 'action': 'policy_grant', 'principal': principal,
            'obj_id': obj_id, 'business_id': biz_id,
            'items': plan,
            'human': f"[dry-run] 将为 {principal} 在 {_fmt_obj(obj_id)}（biz={biz_id or 'ALL'}）授予: {', '.join(actions)}",
        }, args.json)
        return EXIT_OK

    granted = skipped = 0
    for it in plan:
        r = db_grant_policy(**it)
        if r['granted']:
            granted += 1
        else:
            skipped += 1
    _emit({
        'principal': principal, 'obj_id': obj_id, 'business_id': biz_id, 'actions': actions,
        'granted': granted, 'skipped': skipped,
        'human': f"已为 {principal} 在 {_fmt_obj(obj_id)}（biz={biz_id or 'ALL'}）授权 {actions}：新增 {granted} / 跳过 {skipped}",
    }, args.json)
    return EXIT_OK


def cmd_auth_policy_revoke(args):
    principal = (args.user or '').strip()
    if not principal:
        raise CliError(EXIT_PARAM, '用户名必填（--user）', 'policy_revoke')
    actions = _split_csv(args.action)
    if not actions:
        raise CliError(EXIT_PARAM, '动作必填（--action，可逗号分隔：create,update,delete,find,transfer）', 'policy_revoke')
    bad = [a for a in actions if a not in VALID_ACTIONS]
    if bad:
        raise CliError(EXIT_PARAM, f'非法动作: {bad}（仅 {VALID_ACTIONS}）', 'policy_revoke')
    supplier = args.supplier or default_supplier()
    res_type = args.res_type or RES_TYPE_MODEL_INSTANCE
    if res_type not in VALID_RES_TYPES:
        raise CliError(EXIT_PARAM, f'非法资源类型: {res_type}（仅 {VALID_RES_TYPES}）', 'policy_revoke')
    obj_id = args.model or None
    biz_id = args.biz_id or None  # 省略 → 撤销该动作下全部业务（含类级 NULL 与指定业务）

    if args.dry_run:
        _emit({
            'dry_run': True, 'action': 'policy_revoke', 'principal': principal,
            'res_type': res_type, 'obj_id': obj_id, 'business_id': biz_id, 'actions': actions,
            'human': f"[dry-run] 将撤销 {principal} 在 {_fmt_obj(obj_id)}（{res_type}, biz={biz_id or 'ALL'}）的 {actions} 权限",
        }, args.json)
        return EXIT_OK

    total = 0
    for a in actions:
        total += db_revoke_policy(supplier=supplier, principal=principal, res_type=res_type,
                                  obj_id=obj_id, action=a, business_id=biz_id)
    _emit({'deleted': total, 'principal': principal, 'res_type': res_type, 'obj_id': obj_id,
           'business_id': biz_id, 'actions': actions,
           'human': f"已撤销 {principal} 在 {_fmt_obj(obj_id)}（{res_type}, biz={biz_id or 'ALL'}）的 {actions} 权限（共 {total} 条）"}, args.json)
    return EXIT_OK


def cmd_auth_policy_list(args):
    rows = db_list_policies(
        supplier=args.supplier or None,
        principal=(args.user or '').strip() or None,
        res_type=(args.res_type or '').strip() or None,
        obj_id=args.model or None,
        action=(args.action or '').strip() or None,
        business_id=(args.biz_id or '').strip() or None,
    )
    _emit({
        'count': len(rows),
        'policies': rows,
        'human': '\n'.join(
            f"  #{r['id']}\t{r['principal']}\t{r['res_type']}\tobj={r['obj_id'] or 'ALL'}"
            f"\tbiz={r.get('business_id') or 'ALL'}\t{r['action']}\t{r['effect']}"
            for r in rows)
    }, args.json)
    return EXIT_OK


def cmd_auth_policy_grant_scenario(args):
    principal = (args.user or '').strip()
    if not principal:
        raise CliError(EXIT_PARAM, '用户名必填（--user）', 'grant_scenario')
    if not db_exists_user(principal):
        raise CliError(EXIT_PARAM, f'用户不存在: {principal}', 'grant_scenario')
    scenario = (args.scenario or '').strip()
    if scenario not in SCENARIOS:
        raise CliError(EXIT_PARAM, f'未知场景: {scenario}（可用: {list(SCENARIOS.keys())}）', 'grant_scenario')
    models = _split_csv(args.models)
    model = (args.model or '').strip() or None
    biz_id = args.biz_id or None  # 拓扑/转移场景的 biz 作用域；None=全部业务

    try:
        items = db_resolve_scenario(scenario, principal, models=models, model=model,
                                    business_id=biz_id)
    except ValueError as e:
        raise CliError(EXIT_PARAM, str(e), 'grant_scenario')

    if args.dry_run:
        _emit({
            'dry_run': True, 'action': 'grant_scenario', 'scenario': scenario,
            'principal': principal, 'items': items,
            'human': f"[dry-run] 将按场景 {scenario} 为 {principal} 授予 {len(items)} 条策略",
        }, args.json)
        return EXIT_OK

    stats = db_grant_batch(items)
    _emit({
        'scenario': scenario, 'principal': principal, 'items': len(items), **stats,
        'human': f"场景[{scenario}] 为 {principal} 批量授权完成：新增 {stats['granted']} / 跳过 {stats['skipped']} / 失败 {stats['failed']}",
    }, args.json)
    return EXIT_OK


def cmd_auth_action_list(args):
    """列出全部合法 action（用于 --action 参考）。"""
    actions = list(VALID_ACTIONS)
    csv = ','.join(actions)
    _emit({
        'count': len(actions),
        'actions': actions,
        'csv': csv,
        'res_types': list(VALID_RES_TYPES),
        'human': csv,
    }, args.json)
    return EXIT_OK


def cmd_auth_res_type_list(args):
    """列出全部合法 res_type（用于 --res-type 参考；含说明与当前可用动作）。"""
    rows = [{
        'res_type': rt,
        'description': RES_TYPE_DESCRIPTIONS.get(rt, ''),
        'valid_actions': _actions_for_res_type(rt),
    } for rt in VALID_RES_TYPES]
    csv = ','.join(VALID_RES_TYPES)
    _emit({
        'count': len(rows),
        'res_types': rows,
        'csv': csv,
        'human': '\n'.join(
            f"  {r['res_type']}\t{','.join(r['valid_actions']) or '-'}\t{r['description']}"
            for r in rows),
    }, args.json)
    return EXIT_OK


def cmd_auth_model_list(args):
    """列出全部模型 ID（用于 --models 参考）。"""
    model_ids = db_list_model_ids()
    csv = ','.join(model_ids)
    _emit({
        'count': len(model_ids),
        'model_ids': model_ids,
        'csv': csv,
        'human': csv,
    }, args.json)
    return EXIT_OK


# ---------------------------------------------------------------------------
# 解析器注册
# ---------------------------------------------------------------------------
def register(sub, common):
    """把 auth 命令组挂到顶层 sub 解析器下。

    Args:
        sub:    顶层 subparsers（cmdb.py 的 sub）
        common: cmdb.py 的全局选项父解析器（--db/--env/--dry-run/--json 等）
    """
    sp = sub.add_parser('auth', help='鉴权管理（用户 / 策略 / 按场景批量授权）')
    auth_sub = sp.add_subparsers(dest='auth_sub', required=True,
                                 parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))

    # --- user ---
    us = auth_sub.add_parser('user', help='用户管理')
    us_sub = us.add_subparsers(dest='sub', required=True,
                               parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = us_sub.add_parser('create', help='创建用户')
    x.add_argument('--name', required=True, help='用户名（bk_user_name，唯一）')
    x.add_argument('--password', required=True, help='密码明文（werkzeug 哈希后存储）')
    x.add_argument('--role', type=int, default=ROLE_NORMAL, choices=[1, 2],
                   help='角色：1=超级管理员 2=普通用户（默认 2）')
    x.add_argument('--supplier', default=None, help='供应商账户（默认 settings.DEFAULT_SUPPLIER=0）')
    x.set_defaults(func=cmd_auth_user_create)

    x = us_sub.add_parser('list', help='列出全部用户')
    x.set_defaults(func=cmd_auth_user_list)

    x = us_sub.add_parser('update', help='修改用户密码')
    x.add_argument('--name', required=True, help='用户名（bk_user_name）')
    x.add_argument('--password', required=True, help='新密码明文（werkzeug 哈希后存储）')
    x.add_argument('--supplier', default=None, help='供应商账户（默认 settings.DEFAULT_SUPPLIER=0）')
    x.set_defaults(func=cmd_auth_user_update)

    # --- policy ---
    ps = auth_sub.add_parser('policy', help='策略（授权 / 撤销 / 列表）')
    ps_sub = ps.add_subparsers(dest='sub', required=True,
                               parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))

    x = ps_sub.add_parser('grant', help='授予策略（可多动作）')
    x.add_argument('--user', required=True, help='用户名（principal）')
    x.add_argument('--model', default=None,
                   help='obj_id：模型实例=模型 ID；拓扑省略即全部业务(或填 biz_topology)；'
                        '主机转移填 host 或省略。省略=类级=全部模型(NULL)')
    x.add_argument('--res-type', dest='res_type', default=RES_TYPE_MODEL_INSTANCE,
                   choices=list(VALID_RES_TYPES),
                   help=f'资源类型（默认 {RES_TYPE_MODEL_INSTANCE}；拓扑用 {RES_TYPE_BIZ_TOPOLOGY}，'
                        f'主机转移用 {RES_TYPE_HOST_INSTANCE}；可选 {VALID_RES_TYPES}）')
    x.add_argument('--action', required=True, help='动作，逗号分隔：create,update,delete,find,transfer')
    x.add_argument('--supplier', default=None, help='供应商账户（默认 0）')
    x.add_argument('--biz-id', dest='biz_id', default=None,
                   help='业务 ID（拓扑 per-biz 授权；省略=全部业务类级）。biz_topology 资源按此列隔离')
    x.set_defaults(func=cmd_auth_policy_grant)

    x = ps_sub.add_parser('revoke', help='撤销策略（动作可逗号分隔）')
    x.add_argument('--user', required=True, help='用户名（principal）')
    x.add_argument('--model', default=None,
                   help='obj_id：模型实例=模型 ID；拓扑填 biz_topology；主机转移填 host。'
                        '省略则撤销该类级(NULL)及该动作下所有模型级策略')
    x.add_argument('--res-type', dest='res_type', default=RES_TYPE_MODEL_INSTANCE,
                   choices=list(VALID_RES_TYPES),
                   help=f'资源类型（默认 {RES_TYPE_MODEL_INSTANCE}；可选 {VALID_RES_TYPES}）')
    x.add_argument('--action', required=True, help='动作，逗号分隔：create,update,delete,find,transfer')
    x.add_argument('--supplier', default=None, help='供应商账户（默认 0）')
    x.add_argument('--biz-id', dest='biz_id', default=None,
                   help='业务 ID（拓扑 per-biz 撤销；省略=撤销该动作下全部业务，含类级 NULL 与指定业务）')
    x.set_defaults(func=cmd_auth_policy_revoke)

    x = ps_sub.add_parser('list', help='列出策略')
    x.add_argument('--user', default=None, help='按用户名过滤')
    x.add_argument('--model', default=None, help='按模型 ID 过滤')
    x.add_argument('--res-type', dest='res_type', default=None, choices=list(VALID_RES_TYPES),
                   help='按资源类型过滤')
    x.add_argument('--action', default=None, help='按动作过滤')
    x.add_argument('--supplier', default=None, help='按供应商账户过滤')
    x.add_argument('--biz-id', dest='biz_id', default=None, help='按业务 ID 过滤')
    x.set_defaults(func=cmd_auth_policy_list)

    x = ps_sub.add_parser('grant-scenario', help='按场景批量授权')
    x.add_argument('--user', required=True, help='用户名（principal）')
    x.add_argument('--scenario', required=True,
                   help=f'场景名：{"/".join(SCENARIOS.keys())}')
    x.add_argument('--models', default=None, help='显式模型 ID 列表（逗号分隔，覆盖模型场景作用域）')
    x.add_argument('--model', default=None, help='单模型 ID（model-owner 场景必填）')
    x.add_argument('--supplier', default=None, help='供应商账户（默认 0）')
    x.add_argument('--biz-id', dest='biz_id', default=None,
                   help='业务 ID（topo-admin/host-transfer 场景的 biz 作用域；省略=全部业务类级）')
    x.set_defaults(func=cmd_auth_policy_grant_scenario)

    # --- action（只读辅助：列出全部合法动作）---
    ac = auth_sub.add_parser('action', help='动作（action）查询')
    ac_sub = ac.add_subparsers(dest='sub', required=True,
                               parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = ac_sub.add_parser('list', help='列出全部 action（逗号分隔，供 --action 参考）')
    x.set_defaults(func=cmd_auth_action_list)

    # --- res-type（只读辅助：列出全部合法资源类型）---
    rt = auth_sub.add_parser('res-type', help='资源类型（res_type）查询')
    rt_sub = rt.add_subparsers(dest='sub', required=True,
                               parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = rt_sub.add_parser('list', help='列出全部 res_type（含说明/可用动作，供 --res-type 参考）')
    x.set_defaults(func=cmd_auth_res_type_list)

    # --- model（只读辅助：列出全部模型 ID）---
    md = auth_sub.add_parser('model', help='模型（model）查询')
    md_sub = md.add_subparsers(dest='sub', required=True,
                               parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = md_sub.add_parser('list', help='列出全部模型 ID（逗号分隔，供 --models 参考）')
    x.set_defaults(func=cmd_auth_model_list)
