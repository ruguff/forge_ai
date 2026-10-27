from fastapi.testclient import TestClient
from app.main import app

def test_api_schema_available():
    with TestClient(app) as client:
        response = client.get('/openapi.json')
        assert response.status_code == 200
        assert response.json()['paths']
