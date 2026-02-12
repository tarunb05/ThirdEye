import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get('/')
    assert response.status_code == 200
    assert 'ThirdEye' in response.json()['message']

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_analyze_empty_code():
    response = client.post('/api/analyze', json={'code': ''})
    assert response.status_code == 422

def test_analyze_valid_code():
    code = 'pragma solidity ^0.8.0; contract Test { uint x; }'
    response = client.post('/api/analyze', json={'code': code})
    assert response.status_code == 200
    assert 'summary' in response.json()
