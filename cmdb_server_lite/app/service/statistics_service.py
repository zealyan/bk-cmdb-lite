from app.db.executor import query_all, query_one

class StatisticsService:
    
    @staticmethod
    def get_statistics():
        """获取统计数据"""
        sql = "SELECT DISTINCT bk_obj_id FROM cc_ObjAttDes"
        models = query_all(sql, {})
        
        statistics = {}
        
        for model in models:
            model_id = model.get('bk_obj_id')
            if model_id:
                table_name = f"cc_ObjectBase_0_pub_{model_id}"
                count_sql = f"SELECT COUNT(*) as cnt FROM {table_name}"
                result = query_one(count_sql, {})
                statistics[table_name] = result.get('cnt', 0) if result else 0
        
        return statistics