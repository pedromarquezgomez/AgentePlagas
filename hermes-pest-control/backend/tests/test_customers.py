from fastapi.testclient import TestClient
from app.main import app
from app.services.mock_firestore_service import MockFirestoreService
from app.services.customer_service import CustomerService
from app.routes import customers as customers_route

client = TestClient(app)


def test_customer_lifecycle(monkeypatch) -> None:
    # Usar mock db
    mock_db = MockFirestoreService()
    service = CustomerService(mock_db)
    monkeypatch.setattr(customers_route, "customer_service", service)

    # 1. Crear cliente
    response = client.post(
        "/customers",
        json={
            "name": "Bar Pepe Test",
            "email": "pepe@test.com",
            "phone": "+34952000000",
            "customer_type": "HOSPITALITY",
        },
    )
    assert response.status_code == 201
    body = response.json()
    customer_id = body["id"]
    assert customer_id is not None
    assert body["name"] == "Bar Pepe Test"

    # 2. Listar clientes
    response_list = client.get("/customers")
    assert response_list.status_code == 200
    assert len(response_list.json()) == 1

    # 3. Crear Local (Site)
    response_site = client.post(
        f"/customers/{customer_id}/sites",
        json={
            "customer_id": customer_id,
            "name": "Local Principal",
            "address": "Calle Falsa 123",
            "latitude": 36.6,
            "longitude": -4.5,
        },
    )
    assert response_site.status_code == 201
    site_body = response_site.json()
    assert site_body["id"] is not None
    assert site_body["name"] == "Local Principal"

    # 4. Crear Contrato (Contract)
    response_contract = client.post(
        f"/customers/{customer_id}/contracts",
        json={
            "customer_id": customer_id,
            "title": "Mantenimiento Mensual",
            "pest_type": "cucarachas",
            "frequency": "monthly",
            "amount": 100.0,
            "status": "active",
        },
    )
    assert response_contract.status_code == 201
    contract_body = response_contract.json()
    assert contract_body["id"] is not None
    assert contract_body["amount"] == 100.0
