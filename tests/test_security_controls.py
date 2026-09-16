import hashlib
import hmac
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def auth_headers():
    login = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "strong-test-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_invalid_whatsapp_signature_is_rejected():
    body = b'{"entry":[]}'
    response = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert response.status_code in (401, 503)


def test_valid_whatsapp_signature_is_accepted():
    body = b'{"entry":[]}'
    signature = "sha256=" + hmac.new(
        b"test-secret", body, hashlib.sha256
    ).hexdigest()
    response = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 200


def test_private_target_is_blocked():
    response = client.post(
        "/crawl",
        headers=auth_headers(),
        json={"urls": ["http://127.0.0.1:8000/"]},
    )
    assert response.status_code == 400
