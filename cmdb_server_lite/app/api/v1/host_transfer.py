"""
主机转移 API 路由（v1）

对应原项目：
- src/ui/src/store/modules/api/object-main-line-module.js
    - getInstTopo:     POST find/topoinst/biz/{bizId}
    - getInternalTopo: GET topo/internal/{supplierAccount}/{bizId}/with_statistics

提供"转移到业务模块 / 空闲机池"对话框所需的数据：
- POST /host/transfer/topology/biz/<bk_biz_id> : 业务拓扑树（区分 集群分类 / 模块分类，default 标识空闲机池）
- GET  /host/transfer/internal/<bk_supplier_account>/<bk_biz_id> : 空闲机池
- GET  /host/transfer/host/modules : 指定主机的 cc_ModuleHostConfig 绑定（预选 / 写前上下文）
"""
from flask import Blueprint, request, jsonify

from app.service import host_transfer_service
from app.utils.exceptions import APIException, CCErrorCode

host_transfer_bp = Blueprint('host_transfer', __name__, url_prefix='')


@host_transfer_bp.route('/topology/biz/<int:bk_biz_id>', methods=['POST'])
def get_business_module_topo(bk_biz_id):
    """
    获取转移"业务模块"所需的业务拓扑树（集群分类 + 模块分类，含 default 标识）

    PathParams:
        bk_biz_id: 业务ID

    QueryParams:
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: [...], code: 0, message: '' }
    """
    supplier_account = request.args.get('bk_supplier_account', '0')
    try:
        data = host_transfer_service.get_business_module_topo(bk_biz_id, supplier_account)
        return jsonify({
            'result': True,
            'data': data,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取业务拓扑树失败: {str(e)}', 500)


@host_transfer_bp.route('/internal/<bk_supplier_account>/<int:bk_biz_id>', methods=['GET'])
def get_idle_pool(bk_supplier_account, bk_biz_id):
    """
    获取空闲机池（转移到空闲模块使用）

    PathParams:
        bk_supplier_account: 供应商账号
        bk_biz_id: 业务ID

    Returns:
        { result: true, data: { bk_set_id, bk_set_name, module: [...] }, code: 0, message: '' }
    """
    try:
        data = host_transfer_service.get_idle_pool(bk_biz_id, bk_supplier_account)
        return jsonify({
            'result': True,
            'data': data,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取空闲机池失败: {str(e)}', 500)


@host_transfer_bp.route('/host/modules', methods=['GET'])
def get_host_module_config():
    """
    查询指定主机的模块绑定关系（cc_ModuleHostConfig）

    QueryParams:
        bk_biz_id: 业务ID（必填）
        bk_host_id: 主机ID列表，逗号分隔（可选；为空返回该业务全部绑定）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: [...], code: 0, message: '', count: N }
    """
    bk_biz_id = request.args.get('bk_biz_id', type=int)
    if not bk_biz_id:
        raise APIException('缺少业务ID参数 bk_biz_id', 400)

    supplier_account = request.args.get('bk_supplier_account', '0')
    host_id_param = request.args.get('bk_host_id', '')
    host_ids = []
    if host_id_param:
        try:
            host_ids = [int(x) for x in host_id_param.split(',') if x.strip()]
        except ValueError:
            raise APIException('bk_host_id 必须是逗号分隔的整数', 400)

    try:
        data = host_transfer_service.get_host_module_config(bk_biz_id, host_ids, supplier_account)
        return jsonify({
            'result': True,
            'data': data,
            'code': 0,
            'message': '',
            'count': len(data)
        })
    except Exception as e:
        raise APIException(f'查询主机模块绑定失败: {str(e)}', 500)


@host_transfer_bp.route('/modules', methods=['POST'])
def transfer_host_modules():
    """
    执行主机转移到业务模块 / 空闲模块（写操作：修改 cc_ModuleHostConfig）

    Body (JSON):
        bk_biz_id: 业务ID（必填）
        bk_host_id: 主机ID列表（必填）
        module_id: 目标模块ID列表（必填）
        transfer_type: 'business'(默认) | 'idle'
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, code: 0, message: '转移成功', data: {...} }
    """
    data = request.get_json(silent=True) or {}
    bk_biz_id = data.get('bk_biz_id')
    if not bk_biz_id:
        raise APIException('缺少业务ID参数 bk_biz_id', 400)
    try:
        bk_biz_id = int(bk_biz_id)
    except (TypeError, ValueError):
        raise APIException('bk_biz_id 必须为整数', 400)

    raw_host_ids = data.get('bk_host_id') or []
    raw_module_ids = data.get('module_id') or []
    try:
        host_ids = [int(x) for x in raw_host_ids]
        module_ids = [int(x) for x in raw_module_ids]
    except (TypeError, ValueError):
        raise APIException('bk_host_id / module_id 必须为整数列表', 400)
    if not host_ids:
        raise APIException('bk_host_id 不能为空', 400)
    if not module_ids:
        raise APIException('module_id 不能为空', 400)

    transfer_type = data.get('transfer_type') or 'business'
    supplier = data.get('bk_supplier_account') or '0'

    try:
        result = host_transfer_service.transfer_modules(
            bk_biz_id, supplier, host_ids, module_ids, transfer_type
        )
        return jsonify({
            'result': True,
            'code': 0,
            'message': '转移成功',
            'data': result
        })
    except ValueError as e:
        raise APIException(str(e), 400)
    except Exception as e:
        raise APIException(f'主机转移失败: {str(e)}', 500)


@host_transfer_bp.route('/modules/across/biz', methods=['POST'])
def transfer_host_across_biz():
    """
    执行跨业务主机转移（源业务 A → 目标业务 B 的指定模块）

    对应原项目: POST /hosts/modules/across/biz（TransferHostAcrossBusiness）
    解除源业务下这些主机的全部模块绑定，再在目标业务指定模块建立绑定
    （绑定记录 bk_biz_id 写为目标业务）。

    Body (JSON):
        src_bk_biz_id: 源业务ID（必填）
        dst_bk_biz_id: 目标业务ID（必填，须与目标模块所属业务一致）
        bk_host_id: 待转移主机ID列表（必填）
        module_id: 目标业务下的目标模块ID列表（必填）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, code: 0, message: '转移成功', data: {...} }
    """
    data = request.get_json(silent=True) or {}
    src_biz_id = data.get('src_bk_biz_id')
    dst_biz_id = data.get('dst_bk_biz_id')
    if not src_biz_id or not dst_biz_id:
        raise APIException('缺少源/目标业务ID参数 (src_bk_biz_id / dst_bk_biz_id)',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)
    try:
        src_biz_id = int(src_biz_id)
        dst_biz_id = int(dst_biz_id)
    except (TypeError, ValueError):
        raise APIException('src_bk_biz_id / dst_bk_biz_id 必须为整数',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)

    raw_host_ids = data.get('bk_host_id') or []
    raw_module_ids = data.get('module_id') or []
    try:
        host_ids = [int(x) for x in raw_host_ids]
        module_ids = [int(x) for x in raw_module_ids]
    except (TypeError, ValueError):
        raise APIException('bk_host_id / module_id 必须为整数列表',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)
    if not host_ids:
        raise APIException('bk_host_id 不能为空',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)
    if not module_ids:
        raise APIException('module_id 不能为空',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)

    supplier = data.get('bk_supplier_account') or '0'

    try:
        result = host_transfer_service.transfer_across_biz(
            src_biz_id, dst_biz_id, host_ids, module_ids, supplier
        )
        return jsonify({
            'result': True,
            'code': 0,
            'message': '转移成功',
            'data': result
        })
    except ValueError as e:
        raise APIException(str(e), error_code=CCErrorCode.CCErrCommParamsInvalid)
    except Exception as e:
        raise APIException(f'跨业务转移失败: {str(e)}',
                           error_code=CCErrorCode.CCErrTopoInstCreateFailed)
