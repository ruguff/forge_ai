from fastapi.testclient import TestClient
from app.main import app

def test_public_read_contract():
    with TestClient(app,client=('127.0.0.1',50000)) as client:
        assert client.get('/api/store').status_code == 200
        assert client.get('/api/products').status_code == 200
        assert client.post('/api/products',json={}).status_code == 405
