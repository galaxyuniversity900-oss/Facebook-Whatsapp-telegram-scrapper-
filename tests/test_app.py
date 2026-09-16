import os
os.environ["JWT_SECRET"] = "x" * 64
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "strong-test-password"
os.environ["DATABASE_URL"] = "sqlite:///./test_socialintel.db"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["WHATSAPP_APP_SECRET"] = "test-secret"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "verify"

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_auth_and_record():
    login = client.post("/auth/login", json={"email":"admin@example.com","password":"strong-test-password"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/records", headers=headers, json={"source":"test","external_id":"1","text":"hello"})
    assert created.status_code == 200
    result = client.get("/records?q=hello", headers=headers)
    assert result.status_code == 200
    assert result.json()["total"] == 1

def test_records_require_auth():
    assert client.get("/records").status_code == 401
