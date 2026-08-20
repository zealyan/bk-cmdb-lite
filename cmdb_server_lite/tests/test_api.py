"""
API 测试文件
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.config.settings import DevelopmentConfig

@pytest.fixture
def app():
    app = create_app(DevelopmentConfig)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    """测试健康检查"""
    response = client.get('/api/v1/common/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'status' in data
    assert 'database' in data

def test_statistics(client):
    """测试统计接口"""
    response = client.get('/api/v1/common/statistics')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'total_models' in data
