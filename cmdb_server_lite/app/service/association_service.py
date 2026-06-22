from app.db.executor import query_all, query_one, execute
from app.utils.tools import generate_id
from datetime import datetime

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
    
    @staticmethod
    def get_instance_associations(instance_id):
        """获取实例的关联关系"""
        sql = """
            SELECT * FROM cc_InstAsst_0_pub 
            WHERE bk_inst_id = :instance_id OR bk_asst_inst_id = :instance_id
        """
        return query_all(sql, {'instance_id': instance_id})
    
    @staticmethod
    def _count_instance_association(obj_asst_id, **conditions):
        """统计实例关联数量"""
        sql = "SELECT COUNT(*) as count FROM cc_InstAsst_0_pub WHERE bk_obj_asst_id = :bk_obj_asst_id"
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
                obj_asst_id, bk_inst_id=inst_id
            )
            asst_inst_count = AssociationService._count_instance_association(
                obj_asst_id, bk_asst_inst_id=asst_inst_id
            )
            
            if inst_count > 0:
                raise ValueError("1:1 关联不允许创建多个关联实例（源实例已有关联）")
            if asst_inst_count > 0:
                raise ValueError("1:1 关联不允许创建多个关联实例（目标实例已有关联）")
        
        elif mapping == '1:n':
            asst_inst_count = AssociationService._count_instance_association(
                obj_asst_id, bk_asst_inst_id=asst_inst_id
            )
            
            if asst_inst_count > 0:
                raise ValueError("1:n 关联的目标实例已有关联，不能重复关联")
        
        elif mapping == 'n:1':
            inst_count = AssociationService._count_instance_association(
                obj_asst_id, bk_inst_id=inst_id
            )
            
            if inst_count > 0:
                raise ValueError("n:1 关联的源实例已有关联，不能重复关联")
        
        elif mapping == 'n:n':
            pass
    
    @staticmethod
    def create_instance_association(data):
        """创建实例关联"""
        obj_asst_id = data.get('bk_obj_asst_id')
        inst_id = data.get('bk_inst_id')
        asst_inst_id = data.get('bk_asst_inst_id')
        
        if obj_asst_id and inst_id and asst_inst_id:
            AssociationService.check_association_mapping(obj_asst_id, inst_id, asst_inst_id)
        
        data['id'] = generate_id()
        data['_id'] = str(data['id'])
        data.setdefault('bk_supplier_account', '0')
        
        sql = """
            INSERT INTO cc_InstAsst_0_pub
            (_id, id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
            VALUES (:_id, :id, :bk_obj_id, :bk_inst_id, :bk_asst_obj_id, :bk_asst_inst_id, :bk_obj_asst_id, :bk_relation_type_id, :bk_supplier_account)
        """
        execute(sql, data)
        
        return {'id': data['id'], 'result': True}
    
    @staticmethod
    def delete_instance_association(association_id):
        """删除实例关联"""
        sql = "DELETE FROM cc_InstAsst_0_pub WHERE id = :association_id"
        execute(sql, {'association_id': association_id})
        return {'result': True, 'deleted': 1}
    
    @staticmethod
    def find_instance_associations(bk_obj_id, conditions=None):
        """查询实例关联"""
        # 有效的字段列表
        valid_fields = [
            '_id', 'id', 'bk_obj_id', 'bk_inst_id', 
            'bk_asst_obj_id', 'bk_asst_inst_id', 
            'bk_obj_asst_id', 'bk_relation_type_id', 
            'bk_supplier_account'
        ]
        
        base_sql = """
            SELECT ia.*, 
                   oa.bk_obj_asst_name,
                   oa.bk_obj_asst_id,
                   ad.bk_asst_name,
                   oa.target_obj_id,
                   oa.target_obj_name,
                   oa.mapping,
                   oa.on_delete
            FROM cc_InstAsst_0_pub ia
            JOIN cc_ObjAsst oa ON ia.bk_obj_asst_id = oa.bk_obj_asst_id
            JOIN cc_AsstDes ad ON ia.bk_relation_type_id = ad.bk_asst_id
            WHERE ia.bk_obj_id = :bk_obj_id
        """
        params = {'bk_obj_id': bk_obj_id}
        
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
        """获取实例的相关实例"""
        sql = """
            SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                   oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model,
                   oa.mapping, oa.on_delete
            FROM cc_InstAsst_0_pub a
            JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
            JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
            WHERE a.bk_inst_id = :instance_id OR a.bk_asst_inst_id = :instance_id
        """
        
        params = {'instance_id': instance_id}
        
        if model_id:
            sql += " AND a.bk_obj_id = :model_id"
            params['model_id'] = model_id
        
        return query_all(sql, params)