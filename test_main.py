from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_invalid_url_returns_400():
    response = client.post("/summarize", json={"github_url": "https://notgithub.com/test"})
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert "message" in response.json()

def test_fake_repo_returns_404():
    response = client.post("/summarize", json={"github_url": "https://github.com/fakeuser99999/fakerepo99999"})
    assert response.status_code == 404
    assert response.json()["status"] == "error"

def test_missing_field_returns_422():
    response = client.post("/summarize", json={"wrong_field": "oops"})
    assert response.status_code == 422
    assert response.json()["status"] == "error"

def test_empty_body_returns_422():
    response = client.post("/summarize", json={})
    assert response.status_code == 422
    assert response.json()["status"] == "error"