from app.db.executor import query_all, query_one

DEFAULT_CLASSIFICATION_ICON = 'icon-cc-default'
DEFAULT_OBJ_ICON = 'icon-cc-default'

class ClassificationService:
    
    @staticmethod
    def get_all_classifications():
        """获取所有分类"""
        classifications = query_all('classification/select_classifications.sql', {})
        for cls in classifications:
            if not cls.get('bk_classification_icon'):
                cls['bk_classification_icon'] = DEFAULT_CLASSIFICATION_ICON
        return classifications
    
    @staticmethod
    def get_classification_by_id(classification_id):
        """根据ID获取分类"""
        classification = query_one('classification/select_classification_by_id.sql', {
            'classification_id': classification_id
        })
        if classification and not classification.get('bk_classification_icon'):
            classification['bk_classification_icon'] = DEFAULT_CLASSIFICATION_ICON
        return classification
    
    @staticmethod
    def get_models_by_classification(classification_id):
        """获取分类下的模型"""
        models = query_all('classification/select_models_by_classification.sql', {
            'classification_id': classification_id
        })
        for model in models:
            if not model.get('bk_obj_icon'):
                model['bk_obj_icon'] = DEFAULT_OBJ_ICON
        return models
    
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