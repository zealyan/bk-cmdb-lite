from app.db.executor import query_all, query_one

class ClassificationService:
    
    @staticmethod
    def get_all_classifications():
        """获取所有分类"""
        return query_all('classification/select_classifications.sql', {})
    
    @staticmethod
    def get_classification_by_id(classification_id):
        """根据ID获取分类"""
        return query_one('classification/select_classification_by_id.sql', {
            'classification_id': classification_id
        })
    
    @staticmethod
    def get_models_by_classification(classification_id):
        """获取分类下的模型"""
        return query_all('classification/select_models_by_classification.sql', {
            'classification_id': classification_id
        })
    
    @staticmethod
    def get_classifications_with_models():
        """获取分类及其下属模型"""
        classifications = ClassificationService.get_all_classifications()
        result = []
        
        for classification in classifications:
            models = ClassificationService.get_models_by_classification(
                classification.get('bk_classification_id')
            )
            classification['bk_objects'] = models
            result.append(classification)
        
        return result