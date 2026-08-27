from app.db.executor import query_all, query_one, execute
from app.utils.tools import generate_id
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
    def get_association_types():
        """获取所有关联类型"""
        types = query_all('association/select_association_types.sql', {})
        # 补充缺失的字段，避免前端显示 undefined
        for t in types:
            # 给每个类型补充合理的默认值
            if 'src_des' not in t or t.get('src_des') is None:
                t['src_des'] = t.get('bk_asst_name', '指向')
            if 'dest_des' not in t or t.get('dest_des') is None:
                t['dest_des'] = t.get('bk_asst_name', '指向')
        return types
    
    @staticmethod
    def get_object_associations(conditions=None):
        """查询对象关联"""
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
        
        base_sql = """
            SELECT 
                oa.*,
                ad.bk_asst_name
            FROM cc_ObjAsst oa
            JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
        """
        
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
        asst_object_id = result.get('target_obj_id', '')
        
        if mapping == '1:1':
            inst_count = AssociationService._count_instance_association(
                obj_asst_id, object_id, bk_inst_id=inst_id
            )
            asst_inst_count = AssociationService._count_instance_association(
                obj_asst_id, object_id, bk_asst_inst_id=asst_inst_id
            )
            
            if inst_count > 0:
                raise ValueError("1:1 关联不允许创建多个关联实例（源实例已有关联）")
            if asst_inst_count > 0:
                raise ValueError("1:1 关联不允许创建多个关联实例（目标实例已有关联）")
        
        elif mapping == '1:n':
            asst_inst_count = AssociationService._count_instance_association(
                obj_asst_id, object_id, bk_asst_inst_id=asst_inst_id
            )
            
            if asst_inst_count > 0:
                raise ValueError("1:n 关联的目标实例已有关联，不能重复关联")
        
        elif mapping == 'n:1':
            inst_count = AssociationService._count_instance_association(
                obj_asst_id, object_id, bk_inst_id=inst_id
            )
            
            if inst_count > 0:
                raise ValueError("n:1 关联的源实例已有关联，不能重复关联")
        
        elif mapping == 'n:n':
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