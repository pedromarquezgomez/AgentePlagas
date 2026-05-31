from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import audit as audit_route
from app.routes import incidents as incidents_route
from app.services.decision_audit_service import DecisionAuditService
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService


client = TestClient(app)


def test_protected_endpoint_allows_access_when_admin_auth_disabled(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", False)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "")

    response = client.get("/incidents")

    assert response.status_code == 200


def test_protected_endpoint_requires_header_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/incidents")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_protected_endpoint_rejects_wrong_admin_api_key(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/incidents",
        headers={"X-Admin-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert "test-admin-key" not in response.text
    assert "wrong-key" not in response.text


def test_protected_endpoint_accepts_correct_admin_api_key(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    monkeypatch.setattr(incidents_route, "incident_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/incidents",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200


def test_health_remains_public_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_endpoint_is_protected_when_admin_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/audit/decisions")

    assert response.status_code == 401


def test_audit_endpoint_accepts_correct_admin_api_key(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/audit/decisions",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
