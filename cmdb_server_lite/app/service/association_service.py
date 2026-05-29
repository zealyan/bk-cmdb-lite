from app.db.executor import query_all, query_one, execute
from app.utils.tools import generate_id
from datetime import datetime

class AssociationService:
    
    @staticmethod
    def get_association_types():
        """获取所有关联类型"""
        return query_all('association/select_association_types.sql', {})
    
    @staticmethod
    def get_object_associations(conditions=None):
        """查询对象关联"""
        base_sql = """
            SELECT 
                oa.*,
                ad.bk_asst_name,
                ad.src_des,
                ad.dest_des,
                ad.direction
            FROM cc_ObjAsst oa
            JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
        """
        
        if conditions and isinstance(conditions, dict):
            where_clauses = []
            params = {}
            for field, value in conditions.items():
                where_clauses.append(f"oa.{field} = :{field}")
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
                oa.cardinality,
                ad.direction
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
    def create_instance_association(data):
        """创建实例关联"""
        data['id'] = generate_id()
        data['_id'] = data['id']
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
        base_sql = "SELECT * FROM cc_InstAsst_0_pub WHERE bk_obj_id = :bk_obj_id"
        params = {'bk_obj_id': bk_obj_id}
        
        if conditions and isinstance(conditions, dict):
            for field, value in conditions.items():
                base_sql += f" AND {field} = :{field}"
                params[field] = value
        
        return query_all(base_sql, params)
    
    @staticmethod
    def get_related_instances(instance_id, model_id=None):
        """获取实例的相关实例"""
        sql = """
            SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                   oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model
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