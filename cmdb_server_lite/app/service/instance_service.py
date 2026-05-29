from app.db.executor import query_all, query_one, execute, execute_many
from app.db.engine import get_engine
from app.db.sql_loader import load_sql
from app.utils.tools import generate_id
import json
from datetime import datetime

class InstanceService:
    
    @staticmethod
    def _get_table_name(model_id):
        """获取实例表名"""
        return f"cc_ObjectBase_0_pub_{model_id}"
    
    @staticmethod
    def get_instance(model_id, instance_id):
        """获取单个实例"""
        table_name = InstanceService._get_table_name(model_id)
        sql = f"SELECT * FROM {table_name} WHERE id = :instance_id"
        return query_one(sql, {'instance_id': instance_id})
    
    @staticmethod
    def get_instances(model_id, page=1, page_size=20, conditions=None):
        """获取模型实例列表（分页）"""
        table_name = InstanceService._get_table_name(model_id)
        offset = (page - 1) * page_size
        
        sql_parts = [f"SELECT * FROM {table_name}"]
        
        if conditions and isinstance(conditions, dict):
            where_clauses = []
            params = {}
            for field, value in conditions.items():
                where_clauses.append(f"{field} = :{field}")
                params[field] = value
            if where_clauses:
                sql_parts.append("WHERE " + " AND ".join(where_clauses))
        else:
            params = {}
        
        sql_parts.append(f"LIMIT :limit OFFSET :offset")
        params['limit'] = page_size
        params['offset'] = offset
        
        sql = " ".join(sql_parts)
        instances = query_all(sql, params)
        
        count_sql = f"SELECT COUNT(*) as total FROM {table_name}"
        total = query_one(count_sql, {}).get('total', 0)
        
        return {
            'instances': instances,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    @staticmethod
    def count_instances(model_id):
        """统计模型实例数量"""
        table_name = InstanceService._get_table_name(model_id)
        sql = f"SELECT COUNT(*) as total FROM {table_name}"
        result = query_one(sql, {})
        return result.get('total', 0) if result else 0
    
    @staticmethod
    def create_instance(model_id, data):
        """创建实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        data['id'] = generate_id()
        data['_id'] = data['id']
        data.setdefault('bk_supplier_account', '0')
        data.setdefault('create_time', current_time)
        data.setdefault('last_time', current_time)
        
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        execute(sql, data)
        
        return InstanceService.get_instance(model_id, data['id'])
    
    @staticmethod
    def update_instance(model_id, instance_id, data):
        """更新实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        data['last_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        update_fields = []
        params = {'instance_id': instance_id}
        
        for key, value in data.items():
            if key not in ['id', '_id', 'create_time', 'bk_supplier_account']:
                update_fields.append(f"{key} = :{key}")
                params[key] = value
        
        if not update_fields:
            return InstanceService.get_instance(model_id, instance_id)
        
        sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE id = :instance_id"
        execute(sql, params)
        
        return InstanceService.get_instance(model_id, instance_id)
    
    @staticmethod
    def batch_update_instances(model_id, ids, data):
        """批量更新实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        data['last_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        update_fields = []
        params = {'ids': ids}
        
        for key, value in data.items():
            if key not in ['id', '_id', 'create_time', 'bk_supplier_account']:
                update_fields.append(f"{key} = :{key}")
                params[key] = value
        
        if not update_fields:
            return len(ids)
        
        placeholders = ','.join(['?' for _ in ids])
        sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE id IN ({placeholders})"
        
        execute(sql, params)
        return len(ids)
    
    @staticmethod
    def delete_instances(model_id, ids):
        """删除实例（支持批量）"""
        table_name = InstanceService._get_table_name(model_id)
        
        placeholders = ','.join(['?' for _ in ids])
        
        delete_assoc_src_sql = f"DELETE FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN ({placeholders})"
        execute(delete_assoc_src_sql, [model_id] + ids)
        
        delete_assoc_dst_sql = f"DELETE FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN ({placeholders})"
        execute(delete_assoc_dst_sql, [model_id] + ids)
        
        delete_instance_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders})"
        execute(delete_instance_sql, ids)
        
        return len(ids)