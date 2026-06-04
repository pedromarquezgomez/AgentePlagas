from fastapi.testclient import TestClient
from app.main import app
from app.services.mock_firestore_service import MockFirestoreService
from app.services.operational_document_service import OperationalDocumentService
from app.routes import documents as documents_route

client = TestClient(app)


def test_document_versions_lifecycle(monkeypatch) -> None:
    mock_db = MockFirestoreService()
    service = OperationalDocumentService(mock_db)
    monkeypatch.setattr(documents_route, "document_service", service)

    # 1. Crear documento original (crea automáticamente v1)
    response = client.post(
        "/documents",
        json={
            "document_type": "technician_brief",
            "title": "Brief Visita Test",
            "content": "Contenido original v1",
            "status": "draft",
            "generated_by": "admin",
        },
    )
    assert response.status_code == 201
    doc_body = response.json()
    doc_id = doc_body["id"]

    # 2. Listar versiones (debe existir la v1)
    response_versions = client.get(f"/documents/{doc_id}/versions")
    assert response_versions.status_code == 200
    versions = response_versions.json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["content"] == "Contenido original v1"

    # 3. Crear v2
    response_create_v2 = client.post(
        f"/documents/{doc_id}/versions",
        json={
            "content": "Contenido editado v2",
            "generated_by": "admin",
        },
    )
    assert response_create_v2.status_code == 201
    assert response_create_v2.json()["version_number"] == 2

    # 4. Obtener documento principal (debe tener el contenido de v2)
    response_doc = client.get(f"/documents/{doc_id}")
    assert response_doc.status_code == 200
    assert response_doc.json()["content"] == "Contenido editado v2"

    # 5. Listar versiones de nuevo (deben haber v1 y v2)
    response_versions2 = client.get(f"/documents/{doc_id}/versions")
    assert len(response_versions2.json()) == 2
