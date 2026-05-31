from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import documents as documents_route
from app.schemas.incident import IncidentDraft
from app.schemas.technician import TechnicianCreate
from app.schemas.visit import VisitCreate
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService
from app.services.operational_document_service import OperationalDocumentService
from app.services.technician_service import TechnicianService
from app.services.visit_service import VisitService

client = TestClient(app)


def _install_services(monkeypatch) -> tuple[
    OperationalDocumentService,
    IncidentService,
    VisitService,
    TechnicianService,
]:
    firestore_service = MockFirestoreService()
    document_service = OperationalDocumentService(firestore_service)
    incident_service = IncidentService(firestore_service)
    visit_service = VisitService(firestore_service)
    technician_service = TechnicianService(firestore_service)
    monkeypatch.setattr(documents_route, "document_service", document_service)
    monkeypatch.setattr(documents_route, "incident_service", incident_service)
    monkeypatch.setattr(documents_route, "visit_service", visit_service)
    monkeypatch.setattr(documents_route, "technician_service", technician_service)
    return document_service, incident_service, visit_service, technician_service


async def _seed_incident(incident_service: IncidentService) -> str:
    incident = await incident_service.create_incident(
        IncidentDraft(
            conversation_id="telegram:1",
            channel="telegram",
            pest_type="cucarachas",
            location="Torremolinos",
            affected_area="cocina",
            priority="high",
            summary="Cliente informa de cucarachas en cocina.",
        )
    )
    return incident.id or ""


async def _seed_visit(
    incident_service: IncidentService,
    visit_service: VisitService,
    technician_service: TechnicianService,
) -> tuple[str, str]:
    incident_id = await _seed_incident(incident_service)
    technician = await technician_service.create_technician(
        TechnicianCreate(name="Ana Técnica", active=True)
    )
    visit = await visit_service.create_visit(
        VisitCreate(
            incident_id=incident_id,
            technician_id=technician.id,
            scheduled_start="2026-06-01T09:00:00+02:00",
            scheduled_end="2026-06-01T10:00:00+02:00",
            status="scheduled",
            address="Torremolinos",
            notes="Revisar cocina.",
        )
    )
    return incident_id, visit.id or ""


def test_create_document(monkeypatch) -> None:
    _install_services(monkeypatch)

    response = client.post(
        "/documents",
        json={
            "document_type": "incident_summary",
            "incident_id": "incident-1",
            "title": "Resumen",
            "content": "Contenido operativo.",
            "status": "draft",
            "generated_by": "admin",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["id"] is not None
    assert body["document_type"] == "incident_summary"


def test_list_documents_and_filter_by_incident(monkeypatch) -> None:
    _install_services(monkeypatch)
    client.post(
        "/documents",
        json={
            "document_type": "incident_summary",
            "incident_id": "incident-1",
            "title": "Resumen",
            "content": "Contenido.",
        },
    )
    client.post(
        "/documents",
        json={
            "document_type": "work_report_draft",
            "incident_id": "incident-2",
            "title": "Informe",
            "content": "Contenido.",
        },
    )

    response = client.get("/documents?incident_id=incident-1")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["incident_id"] == "incident-1"


def test_get_and_patch_document(monkeypatch) -> None:
    _install_services(monkeypatch)
    created = client.post(
        "/documents",
        json={
            "document_type": "incident_summary",
            "title": "Resumen",
            "content": "Contenido.",
        },
    ).json()

    patch_response = client.patch(
        f"/documents/{created['id']}",
        json={"title": "Resumen revisado", "status": "reviewed"},
    )
    get_response = client.get(f"/documents/{created['id']}")

    assert patch_response.status_code == 200
    assert get_response.json()["title"] == "Resumen revisado"
    assert get_response.json()["status"] == "reviewed"


def test_patch_document_rejects_arbitrary_fields(monkeypatch) -> None:
    _install_services(monkeypatch)
    created = client.post(
        "/documents",
        json={
            "document_type": "incident_summary",
            "title": "Resumen",
            "content": "Contenido.",
        },
    ).json()

    response = client.patch(
        f"/documents/{created['id']}",
        json={"generated_by": "agent_proposal"},
    )

    assert response.status_code == 422


def test_generate_incident_summary_document(monkeypatch) -> None:
    import anyio

    _, incident_service, _, _ = _install_services(monkeypatch)
    incident_id = anyio.run(_seed_incident, incident_service)

    response = client.post(f"/incidents/{incident_id}/generate-summary-document")

    body = response.json()
    assert response.status_code == 200
    assert body["document_type"] == "incident_summary"
    assert body["incident_id"] == incident_id
    assert "cucarachas" in body["content"]
    assert "no certificado legal oficial" in body["content"]


def test_generate_technician_brief(monkeypatch) -> None:
    import anyio

    _, incident_service, visit_service, technician_service = _install_services(monkeypatch)
    _, visit_id = anyio.run(
        _seed_visit,
        incident_service,
        visit_service,
        technician_service,
    )

    response = client.post(f"/visits/{visit_id}/generate-technician-brief")

    body = response.json()
    assert response.status_code == 200
    assert body["document_type"] == "technician_brief"
    assert body["visit_id"] == visit_id
    assert "Ana Técnica" in body["content"]


def test_documents_endpoint_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/documents")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_documents_endpoint_accepts_admin_auth(monkeypatch) -> None:
    _install_services(monkeypatch)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/documents",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
