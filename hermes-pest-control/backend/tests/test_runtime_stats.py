import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.evaluation.runtime_stats import stats_collector

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_stats() -> None:
    """Fixture para resetear las estadísticas acumuladas en memoria en cada test."""
    stats_collector.reset()
    yield
    stats_collector.reset()


def test_stats_collector_initial_state() -> None:
    """Las estadísticas deben inicializarse vacías o con valores por defecto."""
    stats = stats_collector.get_stats()
    assert stats["provider"] == "llm"
    assert stats["model"] == "unknown"
    assert stats["requests"] == 0
    assert stats["fallbacks"] == 0
    assert stats["avg_latency_ms"] == 0.0


def test_stats_collector_record_success() -> None:
    """Verifica que registrar una petición exitosa incrementa las peticiones y calcula bien la latencia promedio."""
    stats_collector.record(
        provider="llm",
        model="gpt-4.1-mini",
        latency_ms=100.0,
        fallback_used=False,
    )
    stats_collector.record(
        provider="llm",
        model="gpt-4.1-mini",
        latency_ms=200.0,
        fallback_used=False,
    )

    stats = stats_collector.get_stats()
    assert stats["provider"] == "llm"
    assert stats["model"] == "gpt-4.1-mini"
    assert stats["requests"] == 2
    assert stats["fallbacks"] == 0
    assert stats["avg_latency_ms"] == 150.0


def test_stats_collector_record_fallback() -> None:
    """Verifica que registrar fallbacks incrementa la cuenta de fallbacks y peticiones."""
    stats_collector.record(
        provider="llm",
        model="gpt-4.1-mini",
        latency_ms=150.0,
        fallback_used=False,
    )
    stats_collector.record(
        provider="llm",
        model="gpt-4.1-mini",
        latency_ms=50.0,
        fallback_used=True,
    )

    stats = stats_collector.get_stats()
    assert stats["provider"] == "llm"
    assert stats["model"] == "gpt-4.1-mini"
    assert stats["requests"] == 2
    assert stats["fallbacks"] == 1
    assert stats["avg_latency_ms"] == 100.0


def test_endpoint_runtime_stats() -> None:
    """Verifica que el endpoint GET /evaluation/runtime-stats devuelva la respuesta correcta."""
    stats_collector.record(
        provider="llm",
        model="gpt-4.1-mini",
        latency_ms=300.0,
        fallback_used=False,
    )

    response = client.get("/evaluation/runtime-stats")
    assert response.status_code == 200

    data = response.json()
    assert data["provider"] == "llm"
    assert data["model"] == "gpt-4.1-mini"
    assert data["requests"] == 1
    assert data["fallbacks"] == 0
    assert data["avg_latency_ms"] == 300.0
