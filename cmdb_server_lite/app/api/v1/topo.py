"""
业务拓扑树 API 路由（v1）

提供与原项目蓝鲸 CMDB 一致的主线拓扑 API：
- /topo/model/mainline - 模型拓扑树（TopoModelMainline）
- /topo/instance/mainline - 实例拓扑树（TopoInstance），支持 with_statistics
- /topo/biz - 业务列表
- /topo/biz/{biz_id}/set - 集群列表
- /topo/set/{set_id}/module - 模块列表
- /topo/biz/{biz_id}/host - 业务下的主机列表（分页）
- /topo/set/{set_id}/host - 集群下的主机列表（分页）
- /topo/module/{module_id}/host - 模块下的主机列表（分页）
- /topo/tree - 完整拓扑树

参考原项目：
- src/source_controller/apigw/servicediscovery/topo/
"""
from flask import Blueprint, request, jsonify
from app.service import topo_service
from app.utils.exceptions import APIException, CCErrorCode
from app.api.v1.common import success_response

topo_bp = Blueprint('topo', __name__, url_prefix='/topo')


@topo_bp.route('/model/mainline', methods=['GET'])
def get_model_mainline():
    """
    获取主线模型拓扑树（TopoModelMainline）

    对应原项目：SearchMainlineModelTopo

    QueryParams:
        supplier_account: 供应商账号，默认 '0'
        with_detail: 是否返回详情，默认 false

    Returns:
        {
            result: true,
            data: { bk_obj_id: 'biz', children: [...] },
            code: 0,
            message: ''
        }
    """
    supplier_account = request.args.get('bk_supplier_account', '0')
    with_detail = request.args.get('with_detail', 'false').lower() == 'true'

    try:
        model_tree = topo_service.get_mainline_model_top(supplier_account)
        return jsonify({
            'result': True,
            'data': model_tree.to_dict(),
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取模型拓扑树失败: {str(e)}', 500)


@topo_bp.route('/instance/mainline', methods=['GET'])
def get_instance_mainline():
    """
    获取主线实例拓扑树（TopoInstance）

    对应原项目：SearchMainlineInstanceTopo

    QueryParams:
        bk_biz_id: 业务ID（必填）
        bk_supplier_account: 供应商账号，默认 '0'
        with_detail: 是否返回详情，默认 false
        with_statistics: 是否返回统计数据，默认 false

    Returns:
        {
            result: true,
            data: { bk_obj_id: 'biz', bk_inst_id: ..., bk_inst_name: ..., child: [...] },
            code: 0,
            message: ''
        }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    if not bk_biz_id:
        raise APIException('缺少业务ID参数 bk_biz_id', 400)

    try:
        bk_biz_id = int(bk_biz_id)
    except ValueError:
        raise APIException('bk_biz_id 必须是整数', 400)

    supplier_account = request.args.get('bk_supplier_account', '0')
    with_detail = request.args.get('with_detail', 'false').lower() == 'true'
    with_statistics = request.args.get('with_statistics', 'false').lower() == 'true'

    try:
        instance_tree = topo_service.get_mainline_instance_topo(
            bk_biz_id=bk_biz_id,
            with_detail=with_detail,
            with_statistics=with_statistics,
            supplier_account=supplier_account
        )
        if not instance_tree:
            return jsonify({
                'result': False,
                'data': None,
                'code': 404,
                'message': f'业务 {bk_biz_id} 不存在'
            })
        return jsonify({
            'result': True,
            'data': instance_tree.to_dict(with_statistics=with_statistics),
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取实例拓扑树失败: {str(e)}', 500)


@topo_bp.route('/instance/children', methods=['GET'])
def get_instance_children():
    """
    获取主线实例某父节点的直接子层（分层懒加载，对齐原项目 lazy-method 规范）

    替代一次性返回整棵 13 万节点树（34MB 响应）的 /topo/instance/mainline，
    前端 bk-big-tree 展开节点时调此接口逐层加载，每层响应仅几百 KB。

    QueryParams:
        bk_biz_id: 业务ID（必填）
        bk_obj_id: 父节点模型ID（biz/set/module/sys/subsys...）（必填）
        bk_inst_id: 父节点实例ID（必填）
        bk_supplier_account: 供应商账号，默认 '0'
        with_statistics: 是否返回聚合主机数 count，默认 true

    Returns:
        { result: true, data: [{bk_obj_id, bk_inst_id, bk_inst_name, default, count, is_leaf}], code: 0 }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    parent_obj_id = request.args.get('bk_obj_id')
    parent_inst_id = request.args.get('bk_inst_id')
    if not bk_biz_id or not parent_obj_id or not parent_inst_id:
        raise APIException('缺少 bk_biz_id / bk_obj_id / bk_inst_id 参数', 400)

    try:
        bk_biz_id = int(bk_biz_id)
        parent_inst_id = int(parent_inst_id)
    except ValueError:
        raise APIException('bk_biz_id / bk_inst_id 必须是整数', 400)

    supplier_account = request.args.get('bk_supplier_account', '0')
    with_statistics = request.args.get('with_statistics', 'true').lower() == 'true'

    try:
        children = topo_service.get_mainline_children(
            bk_biz_id=bk_biz_id,
            parent_obj_id=parent_obj_id,
            parent_inst_id=parent_inst_id,
            with_statistics=with_statistics,
            supplier_account=supplier_account
        )
        if children is None:
            return jsonify({
                'result': False,
                'data': None,
                'code': 404,
                'message': f'业务 {bk_biz_id} 不存在'
            })
        return jsonify({
            'result': True,
            'data': children,
            'code': 0,
            'message': '',
            'count': len(children)
        })
    except Exception as e:
        raise APIException(f'获取子节点失败: {str(e)}', 500)


@topo_bp.route('/instance/path', methods=['GET'])
def get_instance_path():
    """
    批量查询主线实例的祖先路径（biz→...→module），供懒加载树恢复默认选中。

    对齐原项目 find/topopath/biz/{bizId} 的语义：懒加载树初始只含业务根节点，
    转移对话框需要把「默认选中的模块」从深层展开到可见位置，必须知道每个模块
    的完整主线路径（由 bk_parent_id 沿主线逐级上溯得到，支持任意自定义主线层）。

    QueryParams:
        bk_biz_id: 业务ID（必填，用于调试断言）
        bk_inst_id: 主线实例ID列表（逗号分隔）
        bk_obj_id: 起始模型ID（默认 module；biz/set/sys/任意自定义主线层均可）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result, data: [[{bk_obj_id, bk_inst_id, bk_inst_name}...], ...],
          code, message }
        data 与入参 bk_inst_id 顺序一一对应；查不到的实例返回空数组。
    """
    bk_biz_id = request.args.get('bk_biz_id', type=int)
    inst_ids_raw = request.args.get('bk_inst_id', '')
    start_obj_id = request.args.get('bk_obj_id', 'module') or 'module'
    supplier_account = request.args.get('bk_supplier_account', '0')
    ids = []
    for part in inst_ids_raw.split(','):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    if not bk_biz_id or not ids:
        raise APIException('缺少 bk_biz_id / bk_inst_id 参数', 400)

    try:
        chains = []
        for inst_id in ids:
            try:
                chain = topo_service.get_instance_mainline_path(
                    obj_id=start_obj_id,
                    inst_id=inst_id,
                    bk_biz_id=bk_biz_id,
                    supplier_account=supplier_account
                )
                chains.append(chain)
            except Exception:
                chains.append([])
        return jsonify({
            'result': True,
            'data': chains,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取实例路径失败: {str(e)}', 500)


@topo_bp.route('/biz', methods=['GET'])
def get_biz_list():
    """
    获取业务列表

    QueryParams:
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: [...], code: 0 }
    """
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        biz_list = topo_service.get_biz_list(supplier_account)
        return jsonify({
            'result': True,
            'data': biz_list,
            'code': 0,
            'message': '',
            'count': len(biz_list)
        })
    except Exception as e:
        raise APIException(f'获取业务列表失败: {str(e)}', 500)


@topo_bp.route('/biz', methods=['POST'])
def create_biz():
    """
    创建业务（CreateBusiness）

    对应原项目：CreateBusiness。业务是主线拓扑根节点，写入 cc_ApplicationBase，
    bk_biz_id 由全局序列自动发号，bk_biz_name 全局唯一。

    RequestBody:
        {
            "bk_biz_name": "新业务名称",         # 必填，全局唯一
            "bk_supplier_account": "0",          # 可选，默认 '0'
            "bk_biz_maintainer": "admin",        # 可选业务属性（其余业务字段亦可透传）
            "bk_biz_developer": "admin",
            "bk_biz_productor": "admin",
            "bk_biz_tester": "admin",
            "bk_biz_operator": "admin"
        }

    Returns:
        { result: true, bk_error_code: 0, data: { bk_biz_id, bk_biz_name, ... }, code: 0 }

    Errors:
        参数缺失 -> 1199006；重名/唯一约束冲突 -> 1199014；其它创建失败 -> 1101000
    """
    data = request.get_json()
    if not data or not data.get('bk_biz_name'):
        raise APIException('缺少 bk_biz_name 参数',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)

    bk_biz_name = str(data['bk_biz_name']).strip()
    supplier_account = str(data.get('bk_supplier_account', '0')).strip() or '0'

    # 透传其余可选业务属性（bk_biz_name / bk_supplier_account 已单独处理）
    extra = {k: v for k, v in data.items()
             if k not in ('bk_biz_name', 'bk_supplier_account')}

    try:
        biz = topo_service.create_biz(
            bk_biz_name=bk_biz_name,
            supplier_account=supplier_account,
            **extra
        )
        return success_response(biz)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'创建业务失败: {str(e)}',
                           error_code=CCErrorCode.CCErrTopoInstCreateFailed)


@topo_bp.route('/biz/<int:bk_biz_id>/set', methods=['GET'])
def get_biz_set_list(bk_biz_id):
    """
    获取业务下的集群列表（懒加载下一级，带统计）

    PathParams:
        bk_biz_id: 业务ID

    QueryParams:
        bk_supplier_account: 供应商账号，默认 '0'
        with_statistics: 是否返回统计，默认 true

    Returns:
        { result: true, data: [...], code: 0 }
    """
    supplier_account = request.args.get('bk_supplier_account', '0')
    with_statistics = request.args.get('with_statistics', 'true').lower() == 'true'

    try:
        if with_statistics:
            data = topo_service.get_set_list_with_statistics(bk_biz_id, supplier_account)
        else:
            data = topo_service._load_instances('set', bk_biz_id, supplier_account)
        return jsonify({
            'result': True,
            'data': data,
            'code': 0,
            'message': '',
            'count': len(data)
        })
    except Exception as e:
        raise APIException(f'获取集群列表失败: {str(e)}', 500)


@topo_bp.route('/set/<int:bk_set_id>/module', methods=['GET'])
def get_set_module_list(bk_set_id):
    """
    获取集群下的模块列表（懒加载下一级，带统计）

    PathParams:
        bk_set_id: 集群ID

    QueryParams:
        bk_biz_id: 业务ID（必填）
        bk_supplier_account: 供应商账号，默认 '0'
        with_statistics: 是否返回统计，默认 true

    Returns:
        { result: true, data: [...], code: 0 }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    if not bk_biz_id:
        raise APIException('缺少业务ID参数 bk_biz_id', 400)

    try:
        bk_biz_id = int(bk_biz_id)
    except ValueError:
        raise APIException('bk_biz_id 必须是整数', 400)

    supplier_account = request.args.get('bk_supplier_account', '0')
    with_statistics = request.args.get('with_statistics', 'true').lower() == 'true'

    try:
        if with_statistics:
            data = topo_service.get_module_list_with_statistics(bk_set_id, bk_biz_id, supplier_account)
        else:
            data = topo_service._load_instances('module', bk_biz_id, supplier_account)
            data = [d for d in data if d.get('bk_set_id') == bk_set_id]
        return jsonify({
            'result': True,
            'data': data,
            'code': 0,
            'message': '',
            'count': len(data)
        })
    except Exception as e:
        raise APIException(f'获取模块列表失败: {str(e)}', 500)


@topo_bp.route('/count', methods=['GET'])
def get_node_host_count():
    """
    异步获取节点的主机数量统计（单个节点）

    QueryParams:
        bk_obj_id: 节点类型（biz/set/module）
        bk_inst_id: 节点ID
        bk_biz_id: 业务ID（set时必填）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: { count: 5 }, code: 0 }
    """
    bk_obj_id = request.args.get('bk_obj_id')
    bk_inst_id = request.args.get('bk_inst_id')
    bk_biz_id = request.args.get('bk_biz_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    if not bk_obj_id or not bk_inst_id:
        raise APIException('缺少 bk_obj_id 或 bk_inst_id', 400)

    try:
        bk_inst_id = int(bk_inst_id)
    except ValueError:
        raise APIException('bk_inst_id 必须是整数', 400)

    try:
        if bk_obj_id == 'biz':
            count = topo_service.get_biz_host_count(bk_inst_id, supplier_account)
        elif bk_obj_id == 'set':
            if not bk_biz_id:
                raise APIException('set 节点需要 bk_biz_id', 400)
            count = topo_service.get_set_host_count(bk_inst_id, int(bk_biz_id), supplier_account)
        elif bk_obj_id == 'module':
            count = topo_service.get_module_host_count(bk_inst_id, supplier_account)
        else:
            # 自定义主线层（如 appsys）：需 bk_biz_id 递归统计其下主机
            if not bk_biz_id:
                raise APIException(f'{bk_obj_id} 节点需要 bk_biz_id', 400)
            count = topo_service.get_mainline_node_host_count(
                bk_obj_id, bk_inst_id, int(bk_biz_id), supplier_account)

        return jsonify({
            'result': True,
            'data': {'count': count},
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'获取统计失败: {str(e)}', 500)


@topo_bp.route('/statistics', methods=['POST'])
def get_topo_statistics():
    """
    批量获取拓扑节点统计数据（原项目 getTopoStatistics）

    RequestBody:
        {
            "bk_biz_id": 2,
            "condition": [
                {"bk_obj_id": "biz", "bk_inst_id": 2},
                {"bk_obj_id": "set", "bk_inst_id": 10, "bk_biz_id": 2},
                {"bk_obj_id": "module", "bk_inst_id": 100}
            ]
        }

    Returns:
        { result: true, data: [{bk_obj_id, bk_inst_id, host_count, service_instance_count}], code: 0 }
    """
    data = request.get_json()
    if not data or not data.get('condition'):
        raise APIException('缺少 condition 参数', 400)

    bk_biz_id = data.get('bk_biz_id')
    condition = data.get('condition')
    supplier_account = data.get('bk_supplier_account', '0')

    if not isinstance(condition, list):
        raise APIException('condition 必须是数组', 400)

    try:
        # 复用 biz-topo 缓存 O(1) 定位节点聚合 count（对齐原项目 GetTopoNodeHostAndSerInstCount +
        # cacheservice/biz-topo）：避免对 condition 逐节点递归查库（原实现对 1000 节点 ~20s）。
        results = topo_service.get_topo_node_statistics(
            bk_biz_id, condition, supplier_account)

        return jsonify({
            'result': True,
            'data': results,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取统计数据失败: {str(e)}', 500)


@topo_bp.route('/biz/<int:bk_biz_id>/host', methods=['GET'])
def get_biz_hosts(bk_biz_id):
    """
    获取业务下的主机列表（分页）

    PathParams:
        bk_biz_id: 业务ID

    QueryParams:
        page: 页码，默认 1
        page_size: 每页数量，默认 20
        sort: 排序字段，默认 bk_host_id
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: { info: [...], count: ... }, code: 0 }
    """
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort = request.args.get('sort', 'bk_host_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        result = topo_service.get_biz_host_list(
            bk_biz_id=bk_biz_id,
            page=page,
            page_size=page_size,
            sort=sort,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取业务主机列表失败: {str(e)}', 500)


@topo_bp.route('/set/<int:bk_set_id>/host', methods=['GET'])
def get_set_hosts(bk_set_id):
    """
    获取集群下的主机列表（分页）

    PathParams:
        bk_set_id: 集群ID

    QueryParams:
        bk_biz_id: 业务ID（必填）
        page: 页码，默认 1
        page_size: 每页数量，默认 20
        sort: 排序字段，默认 bk_host_id
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: { info: [...], count: ... }, code: 0 }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    if not bk_biz_id:
        raise APIException('缺少业务ID参数 bk_biz_id', 400)

    try:
        bk_biz_id = int(bk_biz_id)
    except ValueError:
        raise APIException('bk_biz_id 必须是整数', 400)

    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort = request.args.get('sort', 'bk_host_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        result = topo_service.get_set_host_list(
            bk_set_id=bk_set_id,
            bk_biz_id=bk_biz_id,
            page=page,
            page_size=page_size,
            sort=sort,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取集群主机列表失败: {str(e)}', 500)


@topo_bp.route('/module/<int:bk_module_id>/host', methods=['GET'])
def get_module_hosts(bk_module_id):
    """
    获取模块下的主机列表（分页）

    PathParams:
        bk_module_id: 模块ID

    QueryParams:
        page: 页码，默认 1
        page_size: 每页数量，默认 20
        sort: 排序字段，默认 bk_host_id
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: { info: [...], count: ... }, code: 0 }
    """
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort = request.args.get('sort', 'bk_host_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        result = topo_service.get_module_host_list(
            bk_module_id=bk_module_id,
            page=page,
            page_size=page_size,
            sort=sort,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取模块主机列表失败: {str(e)}', 500)


@topo_bp.route('/tree', methods=['GET'])
def get_topo_tree():
    """
    获取完整拓扑树（所有业务 + 集群 + 模块）

    QueryParams:
        bk_supplier_account: 供应商账号，默认 '0'
        with_statistics: 是否返回统计数据，默认 false

    Returns:
        { result: true, data: [...], code: 0 }
    """
    supplier_account = request.args.get('bk_supplier_account', '0')
    with_statistics = request.args.get('with_statistics', 'false').lower() == 'true'

    try:
        biz_list = topo_service.get_biz_list(supplier_account)
        tree_data = []
        for biz in biz_list:
            biz_id = biz['bk_biz_id']
            instance_tree = topo_service.get_mainline_instance_topo(
                bk_biz_id=biz_id,
                with_detail=False,
                with_statistics=with_statistics,
                supplier_account=supplier_account
            )
            if instance_tree:
                tree_data.append(instance_tree.to_dict(with_statistics=with_statistics))
        return jsonify({
            'result': True,
            'data': tree_data,
            'code': 0,
            'message': ''
        })
    except Exception as e:
        raise APIException(f'获取拓扑树失败: {str(e)}', 500)


@topo_bp.route('/hosts/search', methods=['POST'])
def search_hosts():
    """
    主机搜索（与原项目 HostCommonSearch 一致的 POST 接口）

    对应原项目: POST /findmany/hosts/search/with_biz

    RequestBody (HostCommonSearch):
        {
            "bk_biz_id": 2,
            "ip": {
                "data": ["192.168.1.1"],
                "exact": 1,
                "flag": "bk_host_innerip|bk_host_outerip"
            },
            "condition": [
                {
                    "bk_obj_id": "host",
                    "fields": [],
                    "condition": [
                        {"field": "bk_host_name", "operator": "$regex", "value": "web"}
                    ]
                },
                {
                    "bk_obj_id": "set",
                    "fields": [],
                    "condition": [
                        {"field": "bk_set_id", "operator": "$eq", "value": 10}
                    ]
                },
                {
                    "bk_obj_id": "module",
                    "fields": [],
                    "condition": [
                        {"field": "bk_module_id", "operator": "$in", "value": [100, 101]}
                    ]
                }
            ],
            "page": {
                "start": 0,
                "limit": 20,
                "sort": "bk_host_id"
            }
        }

    Returns:
        {
            "result": true,
            "data": { "info": [...], "count": 100 },
            "code": 0,
            "message": ""
        }
    """
    data = request.get_json()
    if not data:
        raise APIException('请求体不能为空', 400)

    supplier_account = data.get('bk_supplier_account', '0')

    try:
        result = topo_service.search_hosts(
            params=data,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'主机搜索失败: {str(e)}', 500)


@topo_bp.route('/host/<int:bk_host_id>/topology', methods=['GET'])
def get_host_topology(bk_host_id):
    """
    获取主机的业务拓扑信息

    QueryParams:
        bk_biz_id: 业务ID（可选）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        {
            result: true,
            data: [...],
            code: 0,
            message: ''
        }
    """
    bk_biz_id = request.args.get('bk_biz_id', type=int)
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        result = topo_service.get_host_topology(
            bk_host_id=bk_host_id,
            bk_biz_id=bk_biz_id,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'获取主机拓扑失败: {str(e)}', 500)


@topo_bp.route('/biz/<int:bk_biz_id>/set', methods=['POST'])
def create_set(bk_biz_id):
    """
    创建集群（批量）

    PathParams:
        bk_biz_id: 业务ID

    RequestBody:
        {
            "names": ["集群1", "集群2"]
        }

    Returns:
        {
            result: true,
            data: { created: [...] },
            code: 0,
            message: ''
        }
    """
    data = request.get_json()
    if not data or not data.get('names'):
        raise APIException('缺少 names 参数', 400)

    names = data.get('names')
    if not isinstance(names, list):
        raise APIException('names 必须是数组', 400)

    supplier_account = data.get('bk_supplier_account', '0')

    try:
        result = topo_service.create_set(
            bk_biz_id=bk_biz_id,
            names=names,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'创建集群失败: {str(e)}', 500)


@topo_bp.route('/set/<int:bk_set_id>/module', methods=['POST'])
def create_module(bk_set_id):
    """
    创建模块（批量）

    PathParams:
        bk_set_id: 集群ID

    RequestBody:
        {
            "names": ["模块1", "模块2"]
        }

    Returns:
        {
            result: true,
            data: { created: [...] },
            code: 0,
            message: ''
        }
    """
    data = request.get_json()
    if not data or not data.get('names'):
        raise APIException('缺少 names 参数', 400)

    names = data.get('names')
    if not isinstance(names, list):
        raise APIException('names 必须是数组', 400)

    bk_biz_id = data.get('bk_biz_id')
    supplier_account = data.get('bk_supplier_account', '0')

    try:
        result = topo_service.create_module(
            bk_set_id=bk_set_id,
            names=names,
            bk_biz_id=bk_biz_id,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'创建模块失败: {str(e)}', 500)


@topo_bp.route('/instance/mainline', methods=['POST'])
def create_mainline_instance():
    """
    在主线某父实例下创建任意层级的子实例（通用，对齐上游 SetMainlineInstAssociation）

    替代原专用 create_set/create_module：根据 cc_ObjAsst.bk_mainline 主线顺序，
    在点击节点的【直接子主线层】创建实例，bk_parent_id 指向父实例、bk_biz_id 继承父实例，
    从而严格维持 biz→appsys→zone→set→module 等任意主线顺序（不会在 biz 下错建 set）。

    RequestBody:
        {
            "parent_obj_id": "biz",          # 父模型ID（点击节点所属模型）
            "parent_inst_id": 3,             # 父实例ID（点击节点实例ID）
            "model_id": "appsys",            # 待创建子模型ID（父的直接子主线层）
            "names": ["应用系统A"],          # 实例名称列表（批量）
            "bk_biz_id": 3,                  # 业务ID（父为 biz 时即 parent_inst_id；可缺省自动继承）
            "attrs": { "bk_comment": "..." } # 可选：自定义层额外属性
        }

    Returns:
        全成功: { result: true, bk_error_code: 0, data: { created: [...], error_names: [] } }
        部分/全部失败: { result: false, bk_error_code: 1199014,
                        bk_error_msg: '以下实例创建失败：<name>（<reason>）...',
                        data: { created: [...], error_names: [...] } }
        统一走 BaseResp 结构，失败经全局异常处理器与前端 $handleApiError 统一呈现。
    """
    data = request.get_json() or {}
    parent_obj_id = data.get('parent_obj_id')
    parent_inst_id = data.get('parent_inst_id')
    model_id = data.get('model_id')
    names = data.get('names')
    bk_biz_id = data.get('bk_biz_id')
    attrs = data.get('attrs') or {}
    supplier_account = data.get('bk_supplier_account', '0')

    if not parent_obj_id or parent_inst_id is None:
        raise APIException('缺少 parent_obj_id / parent_inst_id 参数', 400)
    if not model_id:
        raise APIException('缺少 model_id 参数', 400)
    if not names or not isinstance(names, list):
        raise APIException('names 必须是非空数组', 400)

    try:
        result = topo_service.create_mainline_instance(
            parent_obj_id=parent_obj_id,
            parent_inst_id=int(parent_inst_id),
            model_id=model_id,
            names=names,
            bk_biz_id=bk_biz_id,
            supplier_account=supplier_account,
            attrs=attrs
        )
        created = result.get('created') or []
        errors = result.get('error_names') or []
        if errors:
            # 统一业务错误：部分/全部创建失败时，返回与原项目一致的 BaseResp
            # （result:false + bk_error_code + bk_error_msg），由全局 handle_api_exception
            # 与前端统一 $handleApiError 呈现；data 仍携带 created/error_names 供前端
            # 做部分成功展示（已创建的实例进入拓扑树、失败项高亮）。
            # 错误码复用 CCErrCommDuplicateItem(1199014)（与 check_unique 唯一性校验一致）。
            detail = '；'.join(f"{e.get('name')}（{e.get('error')}）" for e in errors)
            return jsonify({
                'result': False,
                'bk_error_code': CCErrorCode.CCErrCommDuplicateItem,
                'bk_error_msg': f'以下实例创建失败：{detail}',
                'data': result
            })
        return success_response(result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'创建主线实例失败: {str(e)}', 500)


@topo_bp.route('/node/<string:bk_obj_id>/<int:bk_inst_id>', methods=['GET'])
def get_node_detail(bk_obj_id, bk_inst_id):
    """
    获取节点详情（biz/set/module）

    Args:
        bk_obj_id: 节点类型（biz/set/module）
        bk_inst_id: 节点实例ID

    QueryParams:
        bk_biz_id: 业务ID（set/module时必填）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: { ... }, code: 0 }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        result = topo_service.get_node_detail(
            bk_obj_id=bk_obj_id,
            bk_inst_id=bk_inst_id,
            bk_biz_id=int(bk_biz_id) if bk_biz_id else None,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'获取节点详情失败: {str(e)}', 500)


@topo_bp.route('/node/<string:bk_obj_id>/<int:bk_inst_id>', methods=['PUT'])
def update_node(bk_obj_id, bk_inst_id):
    """
    更新节点信息（biz/set/module）

    Args:
        bk_obj_id: 节点类型（biz/set/module）
        bk_inst_id: 节点实例ID

    RequestBody:
        {
            "bk_biz_id": 2,
            "bk_set_name": "新名称",      // set节点
            "bk_module_name": "新名称",    // module节点
            "bk_biz_name": "新名称"       // biz节点
        }

    Returns:
        { result: true, data: {}, code: 0 }
    """
    data = request.get_json()
    if not data:
        raise APIException('缺少请求参数', 400)

    try:
        result = topo_service.update_node(
            bk_obj_id=bk_obj_id,
            bk_inst_id=bk_inst_id,
            params=data
        )
        return jsonify({
            'result': True,
            'data': result,
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'更新节点失败: {str(e)}', 500)


@topo_bp.route('/node/<string:bk_obj_id>/<int:bk_inst_id>', methods=['DELETE'])
def delete_node(bk_obj_id, bk_inst_id):
    """
    删除节点（biz/set/module）

    Args:
        bk_obj_id: 节点类型（biz/set/module）
        bk_inst_id: 节点实例ID

    QueryParams:
        bk_biz_id: 业务ID（set/module时必填）
        bk_supplier_account: 供应商账号，默认 '0'

    Returns:
        { result: true, data: {}, code: 0 }
    """
    bk_biz_id = request.args.get('bk_biz_id')
    supplier_account = request.args.get('bk_supplier_account', '0')

    try:
        topo_service.delete_node(
            bk_obj_id=bk_obj_id,
            bk_inst_id=bk_inst_id,
            bk_biz_id=int(bk_biz_id) if bk_biz_id else None,
            supplier_account=supplier_account
        )
        return jsonify({
            'result': True,
            'data': {},
            'code': 0,
            'message': ''
        })
    except APIException:
        raise
    except Exception as e:
        raise APIException(f'删除节点失败: {str(e)}', 500)