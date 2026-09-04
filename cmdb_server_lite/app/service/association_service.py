from app.db.executor import query_all, query_one, execute
from app.utils.tools import generate_id
from app.definitions import (
    PROPERTY_TYPE_INT,
    PROPERTY_TYPE_BOOL,
    NUMERIC_PROPERTY_TYPES
)
from datetime import datetime
import uuid


def get_inst_asst_table_name(obj_id):
    """
    获取实例关联分表名
    格式: cc_InstAsst_0_pub_{obj_id}
    与原项目 tablenames.go GetObjectInstAsstTableName 一致
    """
    return f"cc_InstAsst_0_pub_{obj_id}"


class AssociationService:
    
    @staticmethod
    def get_association_types(supplier: str = '0'):
        """获取所有关联类型（委托给关联类型数据层，保证方向值域与出参类型一致）。

        委托到 app.service.association_type_service.list_association_types：
          - SQL 经方言转译（select_association_types.sql 已带 :bk_supplier_account
            租户过滤参数，不可再用空参调用）；
          - direction 统一归一到 none / src_to_dest / dest_to_src / bidirectional，
            并附 direction_label（中文方向名）；
          - ispre → bool、id → int。
        src_des / dest_des 为空时沿用历史兜底（回退 bk_asst_name），
        避免前端分组标题出现空文案。
        """
        from app.service import association_type_service as kind_svc

        types = kind_svc.list_association_types(supplier)
        for t in types:
            if not t.get('src_des'):
                t['src_des'] = t.get('bk_asst_name') or '指向'
            if not t.get('dest_des'):
                t['dest_des'] = t.get('bk_asst_name') or '指向'
        return types
    
    @staticmethod
    def get_object_associations(conditions=None):
        """查询对象关联（模型间关联定义，cc_ObjAsst × cc_AsstDes）

        主句外置到 app/sql/association/select_object_associations.sql（含 JOIN 出的
        src_des / dest_des / direction 等关联类型属性列），此处仅按调用方条件做
        白名单校验 + 动态 WHERE 拼接；SQL 方言转译由执行层统一负责。
        """
        from app.db.sql_loader import load_sql
        # 有效的字段列表
        valid_fields = [
            '_id', 'id', 'bk_obj_id', 'target_obj_id',
            'target_obj_name', 'bk_asst_id', 'bk_obj_asst_id',
            'bk_obj_asst_name', 'mapping', 'on_delete',
            'creator', 'modifier', 'create_time', 'last_time',
            'bk_supplier_account', 'bk_asst_obj_id'
        ]

        # 字段别名映射（前端使用的字段名 -> 数据库实际字段名）
        field_aliases = {
            'bk_asst_obj_id': 'target_obj_id'  # 前端字段名 -> 数据库字段名
        }

        base_sql = load_sql('association', 'select_object_associations.sql')

        if conditions and isinstance(conditions, dict):
            where_clauses = []
            params = {}
            for field, value in conditions.items():
                # 处理字段别名
                actual_field = field_aliases.get(field, field)
                if actual_field in valid_fields:
                    where_clauses.append(f"oa.{actual_field} = :{field}")
                    params[field] = value
            if where_clauses:
                sql = base_sql + " WHERE " + " AND ".join(where_clauses)
            else:
                sql = base_sql
        else:
            sql = base_sql
            params = {}

        return query_all(sql, params)
    
    @staticmethod
    def get_model_associations(model_id):
        """获取模型的关联关系"""
        sql = """
            SELECT 
                oa.bk_obj_id,
                oa.target_obj_id,
                oa.target_obj_name,
                oa.bk_asst_id AS relation_type_id,
                ad.bk_asst_name AS relation_type_name,
                oa.bk_obj_asst_id,
                oa.bk_obj_asst_name,
                oa.mapping,
                oa.on_delete
            FROM cc_ObjAsst oa
            JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
            WHERE oa.bk_obj_id = :model_id
        """
        return query_all(sql, {'model_id': model_id})

    # ---------------------------------------------------------------------------
    # 通用（非主线）模型关联：创建（幂等）/ 删除（级联实例关联）
    # 与主线 bk_mainline 关联区分：bk_mainline 由专用 mainline 接口管理，
    # 此处只处理普通关联类型（如 default / belong / run / connect 等）。
    # ---------------------------------------------------------------------------
    MAINLINE_ASST_ID = 'bk_mainline'

    @staticmethod
    def _model_exists(obj_id, supplier='0'):
        return query_one(
            "SELECT bk_obj_id, bk_obj_name FROM cc_ObjDes "
            "WHERE bk_obj_id = :o AND bk_supplier_account = :s",
            {'o': obj_id, 's': supplier})

    @staticmethod
    def _asst_type_exists(asst_id, supplier='0'):
        return query_one(
            "SELECT bk_asst_id, bk_asst_name FROM cc_AsstDes "
            "WHERE bk_asst_id = :a AND bk_supplier_account = :s",
            {'a': asst_id, 's': supplier})

    @staticmethod
    def make_obj_asst_id(src_obj_id, asst_id, dst_obj_id):
        """模型关联主键（bk_obj_asst_id）固定格式：{源}_{关联类型}_{目标}。"""
        return f"{src_obj_id}_{asst_id}_{dst_obj_id}"

    @staticmethod
    def create_model_association(src_obj_id, dst_obj_id, asst_id,
                                 mapping='1:n', on_delete='none',
                                 asst_name=None, supplier='0',
                                 on_exist='skip'):
        """创建通用（非主线）模型关联，幂等。

        校验：
          - 关联类型必须存在且不得为 bk_mainline（主线关联由专用接口管理）；
          - 源/目标模型必须存在。
        幂等：bk_obj_asst_id 为固定格式主键。
          - on_exist='skip'：已存在则跳过（返回 existing=True）；
          - on_exist='update'：已存在则更新 mapping/on_delete。

        返回 dict：{bk_obj_asst_id, id, created, updated, existing, src, dst, asst_id}
        """
        if asst_id == AssociationService.MAINLINE_ASST_ID:
            raise ValueError("bk_mainline 为主线专用关联类型，通用模型关联不可使用；请用 mainline 接口")
        asst = AssociationService._asst_type_exists(asst_id, supplier)
        if not asst:
            raise ValueError(f"关联类型不存在: {asst_id}（请先通过 migrate 或 cc_AsstDes 注册）")

        src = AssociationService._model_exists(src_obj_id, supplier)
        if not src:
            raise ValueError(f"源模型不存在: {src_obj_id}")
        dst = AssociationService._model_exists(dst_obj_id, supplier)
        if not dst:
            raise ValueError(f"目标模型不存在: {dst_obj_id}")

        bk_obj_asst_id = AssociationService.make_obj_asst_id(src_obj_id, asst_id, dst_obj_id)
        exist = query_one(
            "SELECT * FROM cc_ObjAsst WHERE bk_obj_asst_id = :aid AND bk_supplier_account = :s",
            {'aid': bk_obj_asst_id, 's': supplier})

        rel_name = asst_name or (asst.get('bk_asst_name') or asst_id)
        display_name = f"{src.get('bk_obj_name')}{rel_name}{dst.get('bk_obj_name')}"

        if exist:
            if on_exist == 'update':
                execute(
                    "UPDATE cc_ObjAsst SET mapping = :m, on_delete = :od, "
                    "modifier = 'admin', last_time = CURRENT_TIMESTAMP "
                    "WHERE bk_obj_asst_id = :aid AND bk_supplier_account = :s",
                    {'m': mapping, 'od': on_delete, 'aid': bk_obj_asst_id, 's': supplier})
                return {'bk_obj_asst_id': bk_obj_asst_id, 'id': exist['id'],
                        'created': False, 'updated': True, 'existing': True,
                        'src': src_obj_id, 'dst': dst_obj_id, 'asst_id': asst_id}
            return {'bk_obj_asst_id': bk_obj_asst_id, 'id': exist['id'],
                    'created': False, 'updated': False, 'existing': True,
                    'src': src_obj_id, 'dst': dst_obj_id, 'asst_id': asst_id}

        new_id = generate_id()
        execute(
            "INSERT INTO cc_ObjAsst "
            "(id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, "
            " bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete, "
            " creator, modifier, bk_supplier_account) "
            "VALUES (:id, :bk_obj_id, :target_obj_id, :target_obj_name, :bk_asst_id, "
            " :bk_obj_asst_id, :bk_obj_asst_name, :mapping, :on_delete, "
            " 'admin', 'admin', :bk_supplier_account)",
            {'id': new_id, 'bk_obj_id': src_obj_id, 'target_obj_id': dst_obj_id,
             'target_obj_name': dst.get('bk_obj_name'),
             'bk_asst_id': asst_id, 'bk_obj_asst_id': bk_obj_asst_id,
             'bk_obj_asst_name': display_name, 'mapping': mapping,
             'on_delete': on_delete, 'bk_supplier_account': supplier})
        return {'bk_obj_asst_id': bk_obj_asst_id, 'id': new_id,
                'created': True, 'updated': False, 'existing': False,
                'src': src_obj_id, 'dst': dst_obj_id, 'asst_id': asst_id}

    @staticmethod
    def delete_model_association(src_obj_id=None, dst_obj_id=None, asst_id=None,
                                 bk_obj_asst_id=None, supplier='0'):
        """删除通用（非主线）模型关联，并级联清理对应实例关联分表。

        定位方式二选一：
          - 直接给 bk_obj_asst_id（主键）；
          - 或给 (src_obj_id, dst_obj_id, asst_id) 计算主键。
        禁止：bk_mainline 主线关联（由专用接口删除）。

        返回 dict：{deleted, bk_obj_asst_id, count, found, inst_deleted}
        """
        if not bk_obj_asst_id:
            if not (src_obj_id and dst_obj_id and asst_id):
                raise ValueError("需提供 bk_obj_asst_id，或 (src_obj_id, dst_obj_id, asst_id) 三元组")
            bk_obj_asst_id = AssociationService.make_obj_asst_id(src_obj_id, asst_id, dst_obj_id)

        row = query_one(
            "SELECT bk_asst_id FROM cc_ObjAsst "
            "WHERE bk_obj_asst_id = :aid AND bk_supplier_account = :s",
            {'aid': bk_obj_asst_id, 's': supplier})
        if not row:
            return {'deleted': False, 'bk_obj_asst_id': bk_obj_asst_id,
                    'count': 0, 'found': False, 'inst_deleted': 0}

        if row.get('bk_asst_id') == AssociationService.MAINLINE_ASST_ID:
            raise ValueError("bk_mainline 为主线专用关联，不可经通用接口删除；请用 mainline 接口")

        # 级联清理所有模型实例关联分表中匹配该 bk_obj_asst_id 的记录
        from app.service.instance_service import InstanceService
        inst_deleted = 0
        for m in InstanceService.list_models():
            oid = m.get('bk_obj_id')
            tbl = get_inst_asst_table_name(oid)
            try:
                r = execute(f'DELETE FROM "{tbl}" WHERE bk_obj_asst_id = :aid',
                            {'aid': bk_obj_asst_id})
                inst_deleted += getattr(r, 'rowcount', 0) or 0
            except Exception:
                pass

        execute(
            "DELETE FROM cc_ObjAsst WHERE bk_obj_asst_id = :aid AND bk_supplier_account = :s",
            {'aid': bk_obj_asst_id, 's': supplier})
        return {'deleted': True, 'bk_obj_asst_id': bk_obj_asst_id,
                'count': 1, 'found': True, 'inst_deleted': inst_deleted}

    @staticmethod
    def get_instance_associations(instance_id, obj_id=None):
        """
        获取实例的关联关系
        如果提供 obj_id，从该模型的分表查询，效率更高
        否则查询所有模型分表（较慢，不推荐）
        """
        if obj_id:
            # 从指定模型的分表查询
            table_name = get_inst_asst_table_name(obj_id)
            sql = f"""
                SELECT * FROM "{table_name}" 
                WHERE bk_inst_id = :instance_id OR bk_asst_inst_id = :instance_id
            """
            return query_all(sql, {'instance_id': instance_id})
        else:
            # 兼容旧逻辑：查询所有分表
            # 先获取所有模型，然后逐个查询分表
            from app.service.instance_service import InstanceService
            models = InstanceService.list_models()
            all_associations = []
            for model in models:
                model_id = model.get('bk_obj_id')
                table_name = get_inst_asst_table_name(model_id)
                try:
                    sql = f"""
                        SELECT * FROM "{table_name}" 
                        WHERE bk_inst_id = :instance_id OR bk_asst_inst_id = :instance_id
                    """
                    results = query_all(sql, {'instance_id': instance_id})
                    all_associations.extend(results)
                except Exception:
                    # 分表可能不存在，跳过
                    pass
            # 去重（同一关联可能存在于多个分表）
            seen_ids = set()
            unique_associations = []
            for assoc in all_associations:
                assoc_id = assoc.get('id')
                if assoc_id and assoc_id not in seen_ids:
                    seen_ids.add(assoc_id)
                    unique_associations.append(assoc)
            return unique_associations
    
    @staticmethod
    def _count_instance_association(obj_asst_id, obj_id, **conditions):
        """统计实例关联数量（指定模型的分表）"""
        table_name = get_inst_asst_table_name(obj_id)
        sql = f'SELECT COUNT(*) as count FROM "{table_name}" WHERE bk_obj_asst_id = :bk_obj_asst_id'
        params = {'bk_obj_asst_id': obj_asst_id}
        
        if 'bk_inst_id' in conditions:
            sql += " AND bk_inst_id = :bk_inst_id"
            params['bk_inst_id'] = conditions['bk_inst_id']
        
        if 'bk_asst_inst_id' in conditions:
            sql += " AND bk_asst_inst_id = :bk_asst_inst_id"
            params['bk_asst_inst_id'] = conditions['bk_asst_inst_id']
        
        result = query_one(sql, params)
        return result.get('count', 0) if result else 0
    
    @staticmethod
    def check_association_mapping(obj_asst_id, inst_id, asst_inst_id):
        """
        检查关联映射规则，根据 mapping 字段校验关联是否合法
        
        参数:
            obj_asst_id: 对象关联ID (bk_obj_asst_id)
            inst_id: 源实例ID
            asst_inst_id: 目标实例ID
        
        返回:
            None: 校验通过
            Exception: 校验失败，包含错误信息
        """
        sql = """
            SELECT mapping, bk_obj_id, target_obj_id 
            FROM cc_ObjAsst 
            WHERE bk_obj_asst_id = :obj_asst_id
        """
        result = query_one(sql, {'obj_asst_id': obj_asst_id})
        
        if not result:
            raise ValueError("关联关系不存在")
        
        mapping = result.get('mapping', '')
        object_id = result.get('bk_obj_id', '')

        # 关联记录在「定义源模型」分表中；这里只统计该分表即可反映整体关联状态。
        # 唯一性校验必须「排除当前这对本身」，否则取消关联后再重新关联同一对端实例
        # 会被误判为「目标/源实例已有关联」而遭到拒绝（bk-cmdb 的 1:1/1:n/n:1 仅约束
        # 对端实例不可再指向「其它」实例，而非禁止重建同一对）。
        table = get_inst_asst_table_name(object_id)

        def _count_other(extra_where: str, **params):
            sql = (f'SELECT COUNT(*) as count FROM "{table}" '
                   f'WHERE bk_obj_asst_id = :oa {extra_where}')
            params['oa'] = obj_asst_id
            res = query_one(sql, params)
            return res.get('count', 0) if res else 0

        if mapping == '1:1':
            # 源、目标各自仅允许一个对端（排除当前这对本身）
            if _count_other("AND bk_inst_id = :inst AND bk_asst_inst_id != :asst",
                            inst=inst_id, asst=asst_inst_id) > 0:
                raise ValueError("1:1 关联不允许：源实例已关联其它目标实例")
            if _count_other("AND bk_asst_inst_id = :asst AND bk_inst_id != :inst",
                            inst=inst_id, asst=asst_inst_id) > 0:
                raise ValueError("1:1 关联不允许：目标实例已关联其它源实例")

        elif mapping == '1:n':
            # 目标实例（n 侧）只能被一个源实例关联，排除当前这对本身
            if _count_other("AND bk_asst_inst_id = :asst AND bk_inst_id != :inst",
                            inst=inst_id, asst=asst_inst_id) > 0:
                raise ValueError("1:n 关联：目标实例已关联其它源实例，不能重复关联")

        elif mapping == 'n:1':
            # 源实例（n 侧）只能关联一个目标，排除当前这对本身
            if _count_other("AND bk_inst_id = :inst AND bk_asst_inst_id != :asst",
                            inst=inst_id, asst=asst_inst_id) > 0:
                raise ValueError("n:1 关联：源实例已关联其它目标实例，不能重复关联")

        elif mapping == 'n:n':
            # 多对多：不限制
            pass
    
    @staticmethod
    def create_instance_association(data):
        """创建实例关联（按模型分表，与原项目一致）"""
        obj_asst_id = data.get('bk_obj_asst_id')
        inst_id = data.get('bk_inst_id')
        asst_inst_id = data.get('bk_asst_inst_id')
        bk_obj_id = data.get('bk_obj_id')
        bk_asst_obj_id = data.get('bk_asst_obj_id')

        # 校验源/目标实例是否存在（遵循原项目 bk-cmdb 逻辑：
        # 创建关联前必须先确认两端实例真实存在，避免产生指向不存在实例的孤儿记录）。
        from app.service.instance_service import InstanceService
        from app.utils.exceptions import ValidationException
        if not bk_obj_id or inst_id is None:
            raise ValidationException('关联源模型或源实例ID缺失')
        if not bk_asst_obj_id or asst_inst_id is None:
            raise ValidationException('关联目标模型或目标实例ID缺失')
        src_instance = InstanceService.get_instance(bk_obj_id, inst_id)
        if not src_instance:
            raise ValidationException(f'关联源实例不存在: {bk_obj_id}/{inst_id}')
        dst_instance = InstanceService.get_instance(bk_asst_obj_id, asst_inst_id)
        if not dst_instance:
            raise ValidationException(f'关联目标实例不存在: {bk_asst_obj_id}/{asst_inst_id}')

        if obj_asst_id and inst_id and asst_inst_id:
            AssociationService.check_association_mapping(obj_asst_id, inst_id, asst_inst_id)

        # 幂等保护：同一对端实例已存在相同关联类型时，直接返回已有记录，
        # 避免（尤其 n:n 场景下）重复点击「关联」产生重复记录。
        src_table = get_inst_asst_table_name(bk_obj_id)
        dup_sql = (
            f'SELECT id FROM "{src_table}" '
            f'WHERE bk_obj_asst_id = :oa AND bk_obj_id = :bk_obj_id '
            f'AND bk_inst_id = :bk_inst_id AND bk_asst_obj_id = :bk_asst_obj_id '
            f'AND bk_asst_inst_id = :bk_asst_inst_id LIMIT 1'
        )
        dup = query_one(dup_sql, {
            'oa': obj_asst_id, 'bk_obj_id': bk_obj_id, 'bk_inst_id': inst_id,
            'bk_asst_obj_id': bk_asst_obj_id, 'bk_asst_inst_id': asst_inst_id,
        })
        if dup:
            return {'id': dup.get('id'), 'result': True, 'duplicated': True}

        data['id'] = generate_id()
        # _id 为 MongoDB 风格文档主键，前端不传，后端兜底生成 UUID，
        # 否则 sqlalchemy 因 INSERT 引用了 :_id 命名参数却无对应值而抛
        # InvalidRequestError: A value is required for bind parameter '_id'
        data.setdefault('_id', str(uuid.uuid4()))
        data.setdefault('bk_supplier_account', '0')
        
        # 按源模型和目标模型分表插入（与原项目一致）
        src_table = get_inst_asst_table_name(bk_obj_id)
        sql = f"""
            INSERT INTO "{src_table}"
            (_id, id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
            VALUES (:_id, :id, :bk_obj_id, :bk_inst_id, :bk_asst_obj_id, :bk_asst_inst_id, :bk_obj_asst_id, :bk_relation_type_id, :bk_supplier_account)
        """
        execute(sql, data)
        
        # 如果源模型和目标模型不同，同时插入到目标模型的关联分表
        if bk_obj_id != bk_asst_obj_id:
            dst_table = get_inst_asst_table_name(bk_asst_obj_id)
            execute(sql.replace(f'"{src_table}"', f'"{dst_table}"'), data)
        
        return {'id': data['id'], 'result': True}
    
    @staticmethod
    def delete_instance_association(association_id, obj_id=None):
        """
        删除实例关联
        由于关联记录在源模型和目标模型两个分表中各存一份（与原项目一致的双向插入），
        删除时需要同时从两个分表删除，避免出现孤儿记录。

        参数:
            association_id: 实例关联记录ID
            obj_id: 当前操作的模型ID（前端调用时传入，用于定位起始分表）

        返回:
            dict: {'result': True, 'deleted': 删除的记录数}
        """
        if not obj_id:
            # 未指定模型，遍历所有模型分表删除
            from app.service.instance_service import InstanceService
            models = InstanceService.list_models()
            deleted_count = 0
            for model in models:
                model_id = model.get('bk_obj_id')
                table_name = get_inst_asst_table_name(model_id)
                try:
                    sql = f'DELETE FROM "{table_name}" WHERE id = :association_id'
                    execute(sql, {'association_id': association_id})
                    deleted_count += 1
                except Exception:
                    pass
            return {'result': True, 'deleted': deleted_count}

        # 1. 先从当前模型分表查询关联记录，获取源模型和目标模型信息
        table_name = get_inst_asst_table_name(obj_id)
        select_sql = f'SELECT bk_obj_id, bk_asst_obj_id FROM "{table_name}" WHERE id = :association_id'
        record = query_one(select_sql, {'association_id': association_id})

        # 2. 删除当前模型分表中的记录
        delete_sql = f'DELETE FROM "{table_name}" WHERE id = :association_id'
        execute(delete_sql, {'association_id': association_id})
        deleted_count = 1

        # 3. 如果能查到记录且源模型与目标模型不同，同时删除目标模型分表中的对应记录
        if record:
            bk_obj_id = record.get('bk_obj_id')
            bk_asst_obj_id = record.get('bk_asst_obj_id')
            # 候选对端模型：源模型与目标模型都可能是对端（当前 obj_id 可能是源也可能是目标）
            counterpart_models = {bk_obj_id, bk_asst_obj_id} - {obj_id}
            for counterpart_model in counterpart_models:
                if not counterpart_model:
                    continue
                counterpart_table = get_inst_asst_table_name(counterpart_model)
                try:
                    cp_delete_sql = f'DELETE FROM "{counterpart_table}" WHERE id = :association_id'
                    execute(cp_delete_sql, {'association_id': association_id})
                    deleted_count += 1
                except Exception:
                    # 对端分表可能不存在，忽略
                    pass

        return {'result': True, 'deleted': deleted_count}
    
    @staticmethod
    def find_instance_associations(bk_obj_id, conditions=None):
        """查询实例关联（从指定模型的分表查询）"""
        table_name = get_inst_asst_table_name(bk_obj_id)
        
        base_sql = f"""
            SELECT ia.*, 
                   oa.bk_obj_asst_name,
                   oa.bk_obj_asst_id,
                   ad.bk_asst_name,
                   oa.target_obj_id,
                   oa.target_obj_name,
                   oa.mapping,
                   oa.on_delete
            FROM "{table_name}" ia
            JOIN cc_ObjAsst oa ON ia.bk_obj_asst_id = oa.bk_obj_asst_id
            JOIN cc_AsstDes ad ON ia.bk_relation_type_id = ad.bk_asst_id
            WHERE ia.bk_obj_id = :bk_obj_id
        """
        params = {'bk_obj_id': bk_obj_id}
        
        valid_fields = [
            '_id', 'id', 'bk_obj_id', 'bk_inst_id', 
            'bk_asst_obj_id', 'bk_asst_inst_id', 
            'bk_obj_asst_id', 'bk_relation_type_id', 
            'bk_supplier_account'
        ]
        
        if conditions and isinstance(conditions, dict):
            for field, value in conditions.items():
                if field in valid_fields:
                    base_sql += f" AND ia.{field} = :{field}"
                    params[field] = value
        
        results = query_all(base_sql, params)
        
        # 补充实例名称信息
        from app.service.instance_service import InstanceService
        for result in results:
            try:
                # 获取源实例名称
                src_instance = InstanceService.get_instance(
                    result.get('bk_obj_id'), 
                    result.get('bk_inst_id')
                )
                if src_instance:
                    result['bk_inst_name'] = src_instance.get('bk_inst_name') or src_instance.get('name')
                
                # 获取目标实例名称
                dest_instance = InstanceService.get_instance(
                    result.get('bk_asst_obj_id'), 
                    result.get('bk_asst_inst_id')
                )
                if dest_instance:
                    result['bk_asst_inst_name'] = dest_instance.get('bk_inst_name') or dest_instance.get('name')
            except Exception:
                pass
        
        return results
    
    @staticmethod
    def search_candidates(params):
        """
        查询「新增关联」弹框的候选目标实例，并联动当前实例是否已关联。

        入参 params:
            obj_id:        当前实例所在模型（关联源/目标定义方）
            inst_id:       当前实例ID
            asst_obj_id:   候选目标模型
            bk_obj_asst_id: 关联类型ID（cc_ObjAsst.bk_obj_asst_id）
            filter:        'all' | 'associated' | 'not_associated'
            page / page_size / conditions / sort / order: 与 advanced_search 一致
        返回:
            { instances, page, page_size, total, associated_ids }
            - instances 的每行带 _is_associated(0/1)
            - associated_ids: 当前实例在该目标模型下已关联实例ID集合
        """
        from app.service.instance_service import InstanceService

        obj_id = params.get('obj_id')
        inst_id = params.get('inst_id')
        asst_obj_id = params.get('asst_obj_id')
        bk_obj_asst_id = params.get('bk_obj_asst_id')
        rel_filter = (params.get('filter') or 'all').strip().lower()

        # 候选模型表与 ID 字段（复用实例表/ID 字段解析，兼容内置模型）
        T = InstanceService._get_table_name(asst_obj_id)
        T_ID = InstanceService._get_id_field(asst_obj_id)
        # 当前实例的关联分表
        A = get_inst_asst_table_name(obj_id)

        # 分页
        page = int(params.get('page') or 1) if params.get('page') else 1
        page_size = int(params.get('page_size') or 20)
        offset = (page - 1) * page_size

        # 排序
        sort = params.get('sort')
        order = (params.get('order') or 'asc').strip()

        # 当前实例关联分表的 JOIN 条件（全部参数化，防注入）
        # 关联具有方向：当前实例 obj_id/inst_id 既可能是源（bk_obj_id/bk_inst_id），
        # 也可能是目标（bk_asst_obj_id/bk_asst_inst_id）。候选实例 T 则对应另一端的
        # bk_asst_obj_id/T_ID 或 bk_obj_id/T_ID。必须用 OR 覆盖两个方向，
        # 否则当弹框从「目标端」打开（如 set 是关联的目标）时，已关联记录无法匹配，
        # 导致「已关联」筛选结果为 0。
        join_sql = f"""
            FROM "{T}" T
            LEFT JOIN "{A}" A
              ON A.bk_obj_asst_id = :bk_obj_asst_id
             AND (
                  ( A.bk_obj_id = :obj_id
                AND A.bk_inst_id = :inst_id
                AND A.bk_asst_obj_id = :asst_obj_id
                AND A.bk_asst_inst_id = T."{T_ID}" )
               OR
                  ( A.bk_asst_obj_id = :obj_id
                AND A.bk_asst_inst_id = :inst_id
                AND A.bk_obj_id = :asst_obj_id
                AND A.bk_inst_id = T."{T_ID}" )
             )
        """
        # 分表过滤条件（决定全部/已关联/未关联）
        assoc_filter_sql = ''
        if rel_filter == 'associated':
            assoc_filter_sql = ' WHERE A.id IS NOT NULL'
        elif rel_filter == 'not_associated':
            assoc_filter_sql = ' WHERE A.id IS NULL'

        pre_params = {
            'obj_id': obj_id,
            'inst_id': inst_id,
            'asst_obj_id': asst_obj_id,
            'bk_obj_asst_id': bk_obj_asst_id
        }

        # ---- 条件筛选（复用 advanced_search 的字段白名单 + 操作符映射）----
        where_clauses = []
        params_dict = dict(pre_params)
        # 列名白名单：仅允许候选模型自身属性作为查询字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(asst_obj_id)
        attr_type_map = {}
        for attr in attributes:
            pid = attr.get('bk_property_id')
            if pid:
                attr_type_map[pid] = attr.get('bk_property_type', '')

        conditions = params.get('conditions')
        if conditions:
            rule_list = conditions.get('rules', []) if isinstance(conditions, dict) else (conditions if isinstance(conditions, list) else [])
            param_counter = 0
            for cond in rule_list:
                if not isinstance(cond, dict):
                    continue
                field = cond.get('field', '')
                op = cond.get('operator', '$eq')
                value = cond.get('value', '')
                field_type = attr_type_map.get(field, '')
                if field_type == PROPERTY_TYPE_BOOL:
                    value = InstanceService._parse_bool_value_for_search(value)
                op_mapping = {
                    'contains': '$regex', 'equal': '$eq', 'not_equal': '$ne',
                    'in': '$in', 'not_in': '$nin', 'greater_than': '$gt',
                    'less_than': '$lt', 'greater_or_equal': '$gte',
                    'less_or_equal': '$lte'
                }
                if op in op_mapping:
                    op = op_mapping[op]
                where_clause, param_counter = InstanceService._build_condition(
                    field, op, value, params_dict, param_counter, field_type)
                if where_clause:
                    # 条件字段属于候选模型 T，需加表别名前缀
                    where_clause = where_clause.replace(f'"{field}"', f'T."{field}"', 1)
                    where_clauses.append(where_clause)

        # 组合 WHERE（分表过滤 + 条件筛选）
        if assoc_filter_sql:
            combined_where = assoc_filter_sql
            if where_clauses:
                combined_where += ' AND ' + ' AND '.join(where_clauses)
        elif where_clauses:
            combined_where = ' WHERE ' + ' AND '.join(where_clauses)
        else:
            combined_where = ''

        # 排序（字段名白名单，对齐 advanced_search）
        sort_clause = ''
        if sort:
            sort_str = str(sort).strip()
            if sort_str.startswith('-'):
                sort_field = sort_str[1:]
                sort_dir = 'DESC'
            else:
                sort_field = sort_str
                sort_dir = order.upper() if order else 'ASC'
            if sort_field.replace('_', '').replace('-', '').isalnum():
                sort_clause = f' ORDER BY T."{sort_field}" {sort_dir}'

        # ---- 主查询 ----
        main_sql = (
            'SELECT T.*, CASE WHEN A.id IS NOT NULL THEN 1 ELSE 0 END AS _is_associated'
            + join_sql
            + combined_where
            + sort_clause
            + ' LIMIT :page_size OFFSET :offset'
        )
        params_dict['page_size'] = page_size
        params_dict['offset'] = offset

        instances = query_all(main_sql, params_dict)

        # 解析 JSON 字段（枚举等），与 advanced_search 一致
        for i in range(len(instances)):
            instances[i] = InstanceService._parse_json_fields(instances[i], asst_obj_id)

        # ---- 总数查询（复用同一 WHERE，去掉 ORDER/LIMIT） ----
        count_sql = (
            'SELECT COUNT(*) as total'
            + join_sql
            + combined_where
        )
        count_result = query_one(count_sql, params_dict)
        total = count_result.get('total', 0) if count_result else 0

        # 已关联实例ID集合（用于前端操作列判定）。
        # 必须基于「全量」查询（不受当前分页/排序影响），否则 all 模式翻页后关联ID集合会缺失。
        # not_associated 场景下恒为空。
        associated_ids = []
        if rel_filter != 'not_associated':
            # 复用同一 JOIN 与条件筛选，强制 A.id IS NOT NULL，仅取候选模型主键列（轻量、无分页）
            cond_part = (' AND ' + ' AND '.join(where_clauses)) if where_clauses else ''
            assoc_ids_sql = (
                f'SELECT T."{T_ID}"'
                + join_sql
                + ' WHERE A.id IS NOT NULL'
                + cond_part
            )
            assoc_rows = query_all(assoc_ids_sql, params_dict)
            associated_ids = [r.get(T_ID) for r in assoc_rows]

        return {
            'instances': instances,
            'page': page,
            'page_size': page_size,
            'total': total,
            'associated_ids': associated_ids
        }

    @staticmethod
    def get_related_instances(instance_id, model_id=None):
        """获取实例的相关实例（从指定模型的分表查询）"""
        if model_id:
            table_name = get_inst_asst_table_name(model_id)
            sql = f"""
                SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                       oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model,
                       oa.mapping, oa.on_delete
                FROM "{table_name}" a
                JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
                JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
                WHERE a.bk_inst_id = :instance_id OR a.bk_asst_inst_id = :instance_id
            """
            params = {'instance_id': instance_id}
            return query_all(sql, params)
        else:
            # 查询所有模型分表
            from app.service.instance_service import InstanceService
            models = InstanceService.list_models()
            all_results = []
            for model in models:
                m_id = model.get('bk_obj_id')
                table_name = get_inst_asst_table_name(m_id)
                try:
                    sql = f"""
                        SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                               oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model,
                               oa.mapping, oa.on_delete
                        FROM "{table_name}" a
                        JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
                        JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
                        WHERE a.bk_inst_id = :instance_id OR a.bk_asst_inst_id = :instance_id
                    """
                    results = query_all(sql, {'instance_id': instance_id})
                    all_results.extend(results)
                except Exception:
                    pass
            # 去重
            seen_ids = set()
            unique_results = []
            for r in all_results:
                r_id = r.get('id')
                if r_id and r_id not in seen_ids:
                    seen_ids.add(r_id)
                    unique_results.append(r)
            return unique_results