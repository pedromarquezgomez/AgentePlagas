from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _preflight(path: str, method: str):
    return client.options(
        path,
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Authorization, Content-Type, X-Admin-API-Key",
        },
    )


def test_technicians_preflight_allows_admin_headers() -> None:
    response = _preflight("/technicians", "POST")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]
    assert "X-Admin-API-Key" in response.headers["access-control-allow-headers"]


def test_generate_incident_summary_preflight_allows_admin_headers() -> None:
    response = _preflight("/incidents/incident-1/generate-summary-document", "POST")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]
    assert "X-Admin-API-Key" in response.headers["access-control-allow-headers"]
