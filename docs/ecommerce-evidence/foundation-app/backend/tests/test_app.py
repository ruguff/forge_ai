from fastapi.testclient import TestClient
from app.main import app
def test_invalid_create_has_no_side_effect():
    with TestClient(app) as client:
        response = client.post('/api/tasks', json={})
        assert response.status_code == 422
        assert client.get('/api/tasks').status_code == 200
