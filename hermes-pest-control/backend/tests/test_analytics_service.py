import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.analytics.contracts import BusinessMetrics
from app.analytics.service import CostEstimator, AnalyticsService
from app.evaluation.runtime_stats import stats_collector
from app.services.mock_firestore_service import MockFirestoreService
from app.main import app

client = TestClient(app)


def test_cost_estimator() -> None:
    # Caso 5: Estimación de costes basada en tokens
    # Caso por defecto
    cost = CostEstimator.estimate_cost(1000, 2000)
    # prompt_tokens * 0.40 / 1e6 = 1000 * 0.4 / 1e6 = 0.0004
    # completion_tokens * 1.60 / 1e6 = 2000 * 1.6 / 1e6 = 0.0032
    # total = 0.0036
    assert cost == 0.0036

    # Caso con variables de entorno personalizadas
    with patch.dict("os.environ", {"LLM_INPUT_COST_PER_1M_TOKENS": "1.00", "LLM_OUTPUT_COST_PER_1M_TOKENS": "2.00"}):
        cost_env = CostEstimator.estimate_cost(1000, 2000)
        # 1000 * 1.00 / 1e6 = 0.001
        # 2000 * 2.00 / 1e6 = 0.004
        # total = 0.005
        assert cost_env == 0.005


@pytest.mark.asyncio
async def test_analytics_service_empty_db() -> None:
    # Caso 1: Sin datos en Firestore, contadores en cero.
    firestore = MockFirestoreService()
    service = AnalyticsService(firestore_service=firestore)

    stats_collector.reset()

    metrics = await service.get_metrics()
    assert metrics.total_conversations == 0
    assert metrics.incidents_created == 0
    assert metrics.visits_proposed == 0
    assert metrics.visits_confirmed == 0
    assert metrics.gmail_drafts_proposed == 0
    assert metrics.gmail_drafts_approved == 0
    assert metrics.human_reviews_required == 0
    assert metrics.human_reviews_completed == 0
    assert metrics.fallback_count == 0
    assert metrics.sla_breaches == 0
    assert metrics.cancelled_incidents == 0
    assert metrics.closed_incidents == 0
    assert metrics.avg_llm_latency_ms == 0.0
    assert metrics.estimated_prompt_tokens == 0
    assert metrics.estimated_completion_tokens == 0
    assert metrics.estimated_total_tokens == 0
    assert metrics.estimated_llm_cost_usd == 0.0


@pytest.mark.asyncio
async def test_analytics_service_incidents() -> None:
    # Caso 2: Incidencias (created, cancelled, closed) agregadas correctamente.
    firestore = MockFirestoreService()
    service = AnalyticsService(firestore_service=firestore)

    # Sembrar incidentes con varios estados
    await firestore.create_document("incidents", {"id": "inc-1", "status": "pending_review"})
    await firestore.create_document("incidents", {"id": "inc-2", "status": "cancelled"})
    await firestore.create_document("incidents", {"id": "inc-3", "status": "closed"})
    await firestore.create_document("incidents", {"id": "inc-4", "status": "in_progress"})

    metrics = await service.get_metrics()
    assert metrics.incidents_created == 4
    assert metrics.cancelled_incidents == 1
    assert metrics.closed_incidents == 1


@pytest.mark.asyncio
async def test_analytics_service_tool_executions_and_sla() -> None:
    # Caso 3: Tool executions (gmail, calendar, human review) y SLA breaches correctamente agregados.
    firestore = MockFirestoreService()
    service = AnalyticsService(firestore_service=firestore)

    # 1. schedule_visit_tool (visits_proposed / visits_confirmed)
    await firestore.create_document("tool_execution_records", {
        "id": "t-1",
        "tool_name": "schedule_visit_tool",
        "review_status": "proposed"
    })
    await firestore.create_document("tool_execution_records", {
        "id": "t-2",
        "tool_name": "schedule_visit_tool",
        "review_status": "approved"
    })

    # 2. gmail.create_draft (gmail_drafts_proposed / gmail_drafts_approved)
    await firestore.create_document("tool_execution_records", {
        "id": "t-3",
        "tool_name": "gmail.create_draft",
        "review_status": "proposed"
    })
    await firestore.create_document("tool_execution_records", {
        "id": "t-4",
        "tool_name": "gmail.create_draft",
        "review_status": "approved"
    })

    # 3. Human Reviews required y completed
    # Review required por decision: require_human_approval, review_status: proposed (pendiente)
    await firestore.create_document("tool_execution_records", {
        "id": "t-5",
        "requires_approval": True,
        "review_status": "proposed"
    })
    # Review required por requires_approval: True, completed por review_status: approved
    await firestore.create_document("tool_execution_records", {
        "id": "t-6",
        "requires_approval": True,
        "review_status": "approved"
    })
    # Review required por requires_approval: True, completed por review_status: dismissed
    await firestore.create_document("tool_execution_records", {
        "id": "t-7",
        "requires_approval": True,
        "review_status": "dismissed"
    })

    # 4. Audit events - SLA breached
    await firestore.create_document("audit_events", {"id": "ae-1", "event_type": "incident_sla_breached"})
    await firestore.create_document("audit_events", {"id": "ae-2", "event_type": "incident_prioritized"})

    metrics = await service.get_metrics()
    assert metrics.visits_proposed == 2
    assert metrics.visits_confirmed == 1
    assert metrics.gmail_drafts_proposed == 2
    assert metrics.gmail_drafts_approved == 1
    assert metrics.human_reviews_required == 3
    assert metrics.human_reviews_completed == 2
    assert metrics.sla_breaches == 1


@pytest.mark.asyncio
async def test_analytics_service_runtime_stats() -> None:
    # Caso 4: Runtime stats (tokens y latencias) registradas y devueltas.
    firestore = MockFirestoreService()
    service = AnalyticsService(firestore_service=firestore)

    stats_collector.reset()

    # Registrar estadísticas de llamadas
    stats_collector.record(
        provider="openai",
        model="gpt-4o",
        latency_ms=1200.0,
        fallback_used=False,
        tokens_used={"prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600}
    )
    stats_collector.record(
        provider="openai",
        model="gpt-4o",
        latency_ms=1800.0,
        fallback_used=True,
        tokens_used={"prompt_tokens": 300, "completion_tokens": 50, "total_tokens": 350}
    )

    metrics = await service.get_metrics()
    assert metrics.avg_llm_latency_ms == 1500.0
    assert metrics.fallback_count == 1
    assert metrics.estimated_prompt_tokens == 800
    assert metrics.estimated_completion_tokens == 150
    assert metrics.estimated_total_tokens == 950
    # coste = (800 * 0.40 + 150 * 1.60) / 1e6 = (320 + 240) / 1e6 = 560 / 1e6 = 0.0006
    assert metrics.estimated_llm_cost_usd == 0.0006


def test_analytics_overview_route_auth(monkeypatch) -> None:
    # Verificar que el endpoint requiere autenticación de administrador
    from app.dependencies import admin_auth
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "secret-admin-key")

    response = client.get("/analytics/overview")
    assert response.status_code == 401


def test_analytics_overview_route_success(monkeypatch) -> None:
    # Mockear las métricas
    async def mock_get_metrics(self):
        return BusinessMetrics(
            total_conversations=10,
            incidents_created=5,
            visits_proposed=2,
            visits_confirmed=1,
            gmail_drafts_proposed=2,
            gmail_drafts_approved=1,
            human_reviews_required=3,
            human_reviews_completed=2,
            fallback_count=1,
            sla_breaches=1,
            cancelled_incidents=1,
            closed_incidents=1,
            avg_llm_latency_ms=1500.0,
            estimated_prompt_tokens=800,
            estimated_completion_tokens=150,
            estimated_total_tokens=950,
            estimated_llm_cost_usd=0.0006,
        )

    monkeypatch.setattr(AnalyticsService, "get_metrics", mock_get_metrics)

    from app.dependencies import admin_auth
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", False)

    response = client.get("/analytics/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["total_conversations"] == 10
    assert body["incidents_created"] == 5
    assert body["visits_confirmed"] == 1
    assert body["sla_breaches"] == 1
    assert body["avg_llm_latency_ms"] == 1500.0
    assert body["estimated_llm_cost_usd"] == 0.0006
