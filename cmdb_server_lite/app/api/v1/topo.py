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
from app.utils.exceptions import APIException

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
    异步获取节点的主机数量统计

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
            raise APIException(f'不支持的对象类型: {bk_obj_id}', 400)

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