from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import technicians as technicians_route
from app.schemas.technician import TechnicianCreate
from app.services.mock_firestore_service import MockFirestoreService
from app.services.technician_service import TechnicianService


client = TestClient(app)


async def _seed_technicians(service: TechnicianService) -> tuple[str, str]:
    active = await service.create_technician(
        TechnicianCreate(
            name="Ana Técnica",
            phone="+34111111111",
            email="ana@example.com",
            active=True,
            service_area="Málaga",
            skills=["cucarachas", "roedores"],
        )
    )
    inactive = await service.create_technician(
        TechnicianCreate(
            name="Luis Técnico",
            active=False,
            service_area="Torremolinos",
            skills=["hormigas"],
        )
    )
    return active.id, inactive.id


def test_create_technician(monkeypatch) -> None:
    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)

    response = client.post(
        "/technicians",
        json={
            "name": "Ana Técnica",
            "phone": "+34111111111",
            "email": "ana@example.com",
            "active": True,
            "service_area": "Málaga",
            "skills": ["cucarachas", "roedores"],
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["id"] is not None
    assert body["name"] == "Ana Técnica"
    assert body["skills"] == ["cucarachas", "roedores"]


def test_list_technicians(monkeypatch) -> None:
    import anyio

    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    anyio.run(_seed_technicians, service)

    response = client.get("/technicians")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2


def test_list_technicians_filters_by_active(monkeypatch) -> None:
    import anyio

    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    active_id, _ = anyio.run(_seed_technicians, service)

    response = client.get("/technicians?active=true")

    body = response.json()
    assert response.status_code == 200
    assert [technician["id"] for technician in body] == [active_id]


def test_get_technician(monkeypatch) -> None:
    import anyio

    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    technician_id, _ = anyio.run(_seed_technicians, service)

    response = client.get(f"/technicians/{technician_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == technician_id
    assert body["name"] == "Ana Técnica"


def test_update_technician(monkeypatch) -> None:
    import anyio

    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    technician_id, _ = anyio.run(_seed_technicians, service)

    response = client.patch(
        f"/technicians/{technician_id}",
        json={
            "phone": "+34222222222",
            "service_area": "Costa del Sol",
            "skills": ["cucarachas"],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["phone"] == "+34222222222"
    assert body["service_area"] == "Costa del Sol"
    assert body["skills"] == ["cucarachas"]


def test_patch_technician_rejects_arbitrary_fields(monkeypatch) -> None:
    import anyio

    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    technician_id, _ = anyio.run(_seed_technicians, service)

    response = client.patch(
        f"/technicians/{technician_id}",
        json={"metadata": {"role": "admin"}},
    )

    assert response.status_code == 422


def test_technicians_endpoint_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/technicians")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_technicians_endpoint_accepts_admin_auth(monkeypatch) -> None:
    service = TechnicianService(MockFirestoreService())
    monkeypatch.setattr(technicians_route, "technician_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/technicians",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
