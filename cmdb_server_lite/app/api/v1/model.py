from flask import Blueprint, jsonify, request
from app.service.model_service import ModelService
from app.service.instance_service import InstanceService
from app.service.association_service import AssociationService
from app.utils.logger import get_logger
from app.utils.exceptions import APIException, ValidationException, NotFoundException
from app.auth.manager import (
    is_enabled, check_instances, pre_authorize_update,
    on_instance_created, permission_for_instances,
)
from app.auth.resource import Action
from app.auth import no_permission

logger = get_logger('api.model')
model_bp = Blueprint('model', __name__)
instance_bp = Blueprint('instance', __name__)

def error_response(message, error_code=1199999):
    """统一错误响应格式 - 与原项目 BaseResp 一致"""
    return jsonify({
        'result': False,
        'bk_error_code': error_code,
        'bk_error_msg': message
    }), 200

def success_response(data=None, message=''):
    """统一成功响应格式 - 与原项目 BaseResp 一致"""
    if data is None:
        data = {}
    return jsonify({
        'result': True,
        'bk_error_code': 0,
        'bk_error_msg': message,
        'data': data
    }), 200

# 模型相关路由 - /api/v1/models/...
@model_bp.route('', methods=['GET'])
def get_models():
    """获取所有模型列表"""
    try:
        models = ModelService.get_all_models()
        return success_response({'models': models})
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return error_response(f'获取模型列表失败: {str(e)}')

@model_bp.route('/<model_id>', methods=['GET'])
def get_model_by_id(model_id):
    """获取单个模型详情"""
    try:
        model = ModelService.get_model_by_id(model_id)
        if model:
            return success_response({'model': model})
        return error_response(f'模型 {model_id} 不存在', 1199019)
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        return error_response(f'获取模型失败: {str(e)}')

@model_bp.route('/<model_id>', methods=['PUT'])
def update_model(model_id):
    """更新模型元数据（停用/启用等）"""
    try:
        data = request.get_json() or {}
        update_data = data.get('data', data)

        model = ModelService.update_model(model_id, update_data)
        if model is None:
            return error_response(f'模型 {model_id} 不存在', 1199019)
        return success_response({'model': model}, '模型更新成功')
    except Exception as e:
        logger.error(f"Error updating model {model_id}: {e}")
        return error_response(f'更新模型失败: {str(e)}')

@model_bp.route('/<model_id>/attributes', methods=['GET'])
def get_model_attributes(model_id):
    """获取模型属性列表

    与原项目 SearchObjectAttributeForWeb 一致:
    过滤掉 bk_issystem=true 和 bk_isapi=true 的系统字段，仅返回前端可见的属性
    """
    try:
        attributes = ModelService.get_model_attributes(model_id, for_web=True)
        return success_response({'attributes': attributes})
    except Exception as e:
        logger.error(f"Error getting model attributes: {e}")
        return error_response(f'获取模型属性失败: {str(e)}')

@model_bp.route('/<model_id>/property-groups', methods=['GET'])
def get_model_property_groups(model_id):
    """获取模型的属性分组"""
    try:
        groups = ModelService.get_model_property_groups(model_id)
        return success_response({'groups': groups})
    except Exception as e:
        logger.error(f"Error getting model property groups: {e}")
        return error_response(f'获取属性分组失败: {str(e)}')

@model_bp.route('/<model_id>/property-groups', methods=['POST'])
def create_model_property_group(model_id):
    """新建属性分组。

    请求体：{ bk_group_name: str(必填), bk_group_index?: int, is_collapse?: bool }
    bk_group_id 由系统随机生成（对齐上游 xid），返回新建分组整行。
    """
    try:
        data = request.get_json() or {}
        bk_group_name = data.get('bk_group_name')
        group = ModelService.create_model_property_group(
            model_id,
            bk_group_name,
            bk_group_index=data.get('bk_group_index', 99),
            is_collapse=data.get('is_collapse', False))
        return success_response({'group': group}, '分组创建成功')
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        logger.error(f"Error creating model property group: {e}")
        return error_response(f'创建属性分组失败: {str(e)}')

@model_bp.route('/<model_id>/property-groups/<group_id>', methods=['PUT'])
def update_model_property_group(model_id, group_id):
    """修改属性分组（显示名 / 排序 / 折叠）。

    请求体（部分字段）：{ bk_group_name?: str, bk_group_index?: int, is_collapse?: bool }
    """
    try:
        data = request.get_json() or {}
        group = ModelService.update_model_property_group(
            model_id,
            group_id,
            bk_group_name=data.get('bk_group_name'),
            bk_group_index=data.get('bk_group_index'),
            is_collapse=data.get('is_collapse'))
        return success_response({'group': group}, '分组更新成功')
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        logger.error(f"Error updating model property group: {e}")
        return error_response(f'更新属性分组失败: {str(e)}')

@model_bp.route('/<model_id>/property-groups/<group_id>', methods=['DELETE'])
def delete_model_property_group(model_id, group_id):
    """删除属性分组（默认分组不可删；其下属性回落 default）。"""
    try:
        ModelService.delete_model_property_group(model_id, group_id)
        return success_response({}, '分组删除成功')
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        logger.error(f"Error deleting model property group: {e}")
        return error_response(f'删除属性分组失败: {str(e)}')

@model_bp.route('/<model_id>/associations', methods=['GET'])
def get_model_associations(model_id):
    """获取模型的关联关系"""
    try:
        associations = AssociationService.get_model_associations(model_id)
        return success_response({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting model associations: {e}")
        return error_response(f'获取关联关系失败: {str(e)}')

@model_bp.route('/<model_id>/instances', methods=['GET'])
def get_model_instances(model_id):
    """获取模型实例列表（分页）"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        conditions = {}
        search_field = request.args.get('search_field')
        search_value = request.args.get('search_value')
        
        if search_field and search_value:
            conditions[search_field] = search_value
        
        result = InstanceService.get_instances(model_id, page, page_size, conditions)
        return success_response(result)
    except Exception as e:
        logger.error(f"Error getting model instances: {e}")
        return error_response(f'获取实例列表失败: {str(e)}')

@model_bp.route('/<model_id>/instances/search', methods=['POST'])
def search_model_instances(model_id):
    """高级搜索模型实例"""
    try:
        data = request.get_json() or {}
        result = InstanceService.advanced_search(model_id, data)
        return success_response(result)
    except Exception as e:
        logger.error(f"Error searching model instances: {e}")
        return error_response(f'搜索实例失败: {str(e)}')

@model_bp.route('/<model_id>/instances/<instance_id>', methods=['GET'])
def get_instance(model_id, instance_id):
    """获取单个实例详情"""
    try:
        instance = InstanceService.get_instance(model_id, instance_id)
        if instance:
            return success_response({'instance': instance})
        return error_response(f'实例 {instance_id} 不存在', 1199019)
    except Exception as e:
        logger.error(f"Error getting instance: {e}")
        return error_response(f'获取实例失败: {str(e)}')



@model_bp.route('/<model_id>/instances/check-unique', methods=['POST'])
def check_instance_unique(model_id):
    """校验实例数据的唯一性"""
    try:
        data = request.get_json() or {}
        instance_data = data.get('data', {})
        exclude_instance_id = data.get('exclude_instance_id')

        duplicates = InstanceService.check_unique(model_id, instance_data, exclude_instance_id)
        return success_response({
            'is_unique': len(duplicates) == 0,
            'duplicates': duplicates
        })
    except Exception as e:
        logger.error(f"Error checking unique for {model_id}: {e}")
        return error_response(f'校验唯一性失败: {str(e)}')

@model_bp.route('/<model_id>/instances', methods=['POST'])
def create_instance(model_id):
    """创建新的模型实例"""
    try:
        data = request.get_json() or {}
        instance_data = data.get('data', {})

        # 模式 B：打标创建者（用于「创建者自管」实例级判定），写入前 stamp
        if is_enabled():
            from app.auth.identity import current_user
            instance_data['creator'] = current_user()

        result = InstanceService.create_instance(model_id, instance_data)

        # 模式 B：创建成功后写「创建者自动授权」策略（对齐 RegisterResourceCreatorAction）
        if is_enabled():
            on_instance_created(model_id)

        return success_response(result, '实例创建成功')
    except APIException as e:
        # 业务异常统一上抛，由全局 handle_api_exception 以
        # HTTP 200 + BaseResp（result:false + bk_error_code）统一返回，
        # 避免端点各自返回非 2xx 状态码，破坏与原项目一致的响应约定。
        raise
    except Exception as e:
        logger.error(f"Error creating instance: {e}")
        return error_response(f'创建实例失败: {str(e)}')

@model_bp.route('/<model_id>/instances/<instance_id>', methods=['PUT'])
def update_instance(model_id, instance_id):
    """更新单个实例"""
    try:
        data = request.get_json() or {}
        instance_data = data.get('data', {})

        # 模式 B：打标最后修改者（bk_modifier 维度；对齐上游 owner/modifier），写入前 stamp。
        # 仅 host 等含 modifier 列的表会落库；自定义模型无该列时由 service 层 real_cols 收敛丢弃。
        if is_enabled():
            from app.auth.identity import current_user
            instance_data['modifier'] = current_user()

        # 模式 B：实例级鉴权（supplier 隔离 / 创建者自管 / 模型级策略）
        if is_enabled():
            deny = check_instances(model_id, [int(instance_id)], Action.UPDATE)
            if deny:
                return no_permission(
                    permission_for_instances(model_id, [int(instance_id)], Action.UPDATE, deny))

        result = InstanceService.update_instance(model_id, instance_id, instance_data)
        return success_response(result, '实例更新成功')
    except APIException as e:
        # 业务异常统一上抛，由全局 handle_api_exception 以
        # HTTP 200 + BaseResp（result:false + bk_error_code）统一返回，
        # 避免端点各自返回非 2xx 状态码，破坏与原项目一致的响应约定。
        raise
    except Exception as e:
        logger.error(f"Error updating instance: {e}")
        return error_response(f'更新实例失败: {str(e)}')

@model_bp.route('/<model_id>/instances', methods=['PUT'])
def batch_update_instances(model_id):
    """批量更新实例"""
    try:
        data = request.get_json() or {}

        # 形态一：逐条 update 数组 → 收敛为一组实例 ID
        if 'update' in data:
            ids = [item.get('inst_id') for item in data['update']
                   if item.get('inst_id') is not None]
            # 模式 B：批量更新预校验（文档 §4.2-4.4）；任一实例无权 → 整体拒绝，不执行写
            if is_enabled():
                _, deny, permission = pre_authorize_update(model_id, ids)
                if deny:
                    return no_permission(permission)
            updated_count = 0
            for item in data['update']:
                inst_id = item.get('inst_id')
                datas = item.get('datas', {})
                if inst_id:
                    InstanceService.update_instance(model_id, inst_id, datas)
                    updated_count += 1
            return success_response({
                'updated_count': updated_count
            }, f'成功更新 {updated_count} 个实例')
        # 形态二：按 ids 批量同值
        elif 'ids' in data and 'data' in data:
            ids = data['ids']
            update_data = data['data']
            # 模式 B：批量更新预校验；任一实例无权 → 整体拒绝，不执行写
            if is_enabled():
                _, deny, permission = pre_authorize_update(model_id, ids)
                if deny:
                    return no_permission(permission)
            updated_count = InstanceService.batch_update_instances(model_id, ids, update_data)
            return success_response({
                'updated_count': updated_count,
                'updated_ids': ids
            }, f'成功更新 {updated_count} 个实例')
        else:
            return error_response('请求格式无效', 1199006)
    except ValidationException as e:
        # 业务异常统一上抛，由全局 handle_api_exception 以
        # HTTP 200 + BaseResp（result:false + bk_error_code）统一返回，
        # 避免端点各自返回非 2xx 状态码，破坏与原项目一致的响应约定。
        raise
    except APIException as e:
        # 业务异常统一上抛，由全局 handle_api_exception 以
        # HTTP 200 + BaseResp（result:false + bk_error_code）统一返回，
        # 避免端点各自返回非 2xx 状态码，破坏与原项目一致的响应约定。
        raise
    except Exception as e:
        logger.error(f"Error updating instances: {e}")
        return error_response(f'批量更新失败: {str(e)}')

@model_bp.route('/<model_id>/instances', methods=['DELETE'])
def delete_instances(model_id):
    """删除实例（支持批量）"""
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])

        if not ids:
            return error_response('未提供实例ID', 1199006)

        # 模式 B：实例级鉴权（supplier 隔离 / 创建者自管 / 模型级策略）；
        # 任一实例无权 → 整体拒绝，不执行任何删除
        if is_enabled():
            deny = check_instances(model_id, ids, Action.DELETE)
            if deny:
                return no_permission(permission_for_instances(model_id, ids, Action.DELETE, deny))

        deleted_count = InstanceService.delete_instances(model_id, ids)
        return success_response({
            'deleted_count': deleted_count,
            'ids': ids
        }, f'成功删除 {deleted_count} 个实例')
    except Exception as e:
        logger.error(f"Error deleting instances: {e}")
        return error_response(f'删除实例失败: {str(e)}')

@model_bp.route('/<model_id>/instances/check-associations', methods=['POST'])
def check_associations(model_id):
    """检查实例关联数量"""
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        
        source_count = 0
        target_count = 0
        
        for instance_id in ids:
            associations = AssociationService.get_instance_associations(instance_id)
            for assoc in associations:
                if assoc.get('bk_obj_id') == model_id and assoc.get('bk_inst_id') == instance_id:
                    source_count += 1
                elif assoc.get('bk_asst_obj_id') == model_id and assoc.get('bk_asst_inst_id') == instance_id:
                    target_count += 1
        
        return success_response({
            'total_associations': source_count + target_count,
            'source_associations': source_count,
            'target_associations': target_count,
            'instance_count': len(ids),
            'model_id': model_id
        })
    except Exception as e:
        logger.error(f"Error checking associations: {e}")
        return error_response(f'检查关联失败: {str(e)}')

# 实例相关路由 - /api/v1/instances/...
@instance_bp.route('/<instance_id>/associations', methods=['GET'])
def get_instance_associations(instance_id):
    """获取单个实例的关联关系

    obj_id 为可选的性能参数：传入时直接定位该模型的 cc_InstAsst_* 分表，
    不传则退化为遍历所有模型分表（慢路径）。该参数原由 association.py 中
    重复的 /api/instances/<id>/associations 路由提供，API 前缀对齐时移除了
    那条从未被调用的路由，故在此处补齐能力，避免丢失分表直查优化。
    """
    try:
        obj_id = request.args.get('obj_id')
        associations = AssociationService.get_instance_associations(instance_id, obj_id)
        return success_response({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting instance associations: {e}")
        return error_response(f'获取关联关系失败: {str(e)}')

@instance_bp.route('/<instance_id>/related', methods=['GET'])
def get_related_instances(instance_id):
    """获取实例的关联实例详情"""
    try:
        model_id = request.args.get('model_id')
        related = InstanceService.get_related_instances(instance_id, model_id)
        return success_response({'related': related})
    except Exception as e:
        logger.error(f"Error getting related instances: {e}")
        return error_response(f'获取关联实例失败: {str(e)}')


@model_bp.route('/instances/count', methods=['POST'])
def get_instances_count():
    """批量获取模型实例数量统计"""
    try:
        data = request.get_json() or {}
        obj_ids = data.get('obj_ids', [])
        
        if not obj_ids:
            return success_response({'counts': []})
        
        counts = []
        for obj_id in obj_ids:
            try:
                count = InstanceService.count_instances(obj_id)
                counts.append({
                    'bk_obj_id': obj_id,
                    'inst_count': count
                })
            except Exception as e:
                logger.error(f"Error counting instances for {obj_id}: {e}")
                counts.append({
                    'bk_obj_id': obj_id,
                    'inst_count': 0,
                    'error': str(e)
                })
        
        return success_response({'counts': counts})
    except Exception as e:
        logger.error(f"Error getting instances count: {e}")
        return error_response(f'获取实例数量失败: {str(e)}')