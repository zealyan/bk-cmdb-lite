"""
数据库执行测试
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.config.settings import DevelopmentConfig
from app.db.engine import init_db, get_engine
from app.db.executor import query_all, query_one, execute

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(DevelopmentConfig)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_database_connection():
    """测试数据库连接"""
    config = DevelopmentConfig()
    engine = init_db(config)
    assert engine is not None
    
    # 测试执行查询
    result = query_one("SELECT 1 as test")
    assert result is not None
    assert result['test'] == 1

def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/api/v1/common/health')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert 'service' in data

def test_index_endpoint(client):
    """测试根路径端点"""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data
    assert data['message'] == 'CMDB Server Lite API'
