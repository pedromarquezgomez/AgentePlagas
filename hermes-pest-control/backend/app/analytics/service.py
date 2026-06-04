import os
from typing import Any

from app.analytics.contracts import BusinessMetrics
from app.evaluation.runtime_stats import stats_collector
from app.services.firestore_factory import get_firestore_service


class CostEstimator:
    @staticmethod
    def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
        try:
            input_cost_per_1m = float(os.getenv("LLM_INPUT_COST_PER_1M_TOKENS", "0.40"))
            output_cost_per_1m = float(os.getenv("LLM_OUTPUT_COST_PER_1M_TOKENS", "1.60"))
        except ValueError:
            input_cost_per_1m = 0.40
            output_cost_per_1m = 1.60
        cost = (prompt_tokens * input_cost_per_1m + completion_tokens * output_cost_per_1m) / 1_000_000.0
        return round(cost, 4)


class AnalyticsService:
    def __init__(self, firestore_service: Any = None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def get_metrics(self) -> BusinessMetrics:
        # 1. Consultar conversaciones
        conversations = await self.firestore_service.list_documents("conversations")
        total_conversations = len(conversations)

        # 2. Consultar incidentes
        incidents = await self.firestore_service.list_documents("incidents")
        incidents_created = len(incidents)
        cancelled_incidents = sum(1 for inc in incidents if inc.get("status") == "cancelled")
        closed_incidents = sum(1 for inc in incidents if inc.get("status") == "closed")

        # 3. Consultar ejecuciones de herramientas
        tool_records = await self.firestore_service.list_documents("tool_execution_records")
        visits_proposed = sum(1 for r in tool_records if r.get("tool_name") == "schedule_visit_tool")
        visits_confirmed = sum(
            1 for r in tool_records
            if r.get("tool_name") == "schedule_visit_tool" and r.get("review_status") == "approved"
        )
        gmail_drafts_proposed = sum(1 for r in tool_records if r.get("tool_name") == "gmail.create_draft")
        gmail_drafts_approved = sum(
            1 for r in tool_records
            if r.get("tool_name") == "gmail.create_draft" and r.get("review_status") == "approved"
        )

        human_reviews_required = sum(
            1 for r in tool_records
            if r.get("requires_approval") is True or r.get("decision") == "require_human_approval"
        )
        human_reviews_completed = sum(
            1 for r in tool_records
            if (r.get("requires_approval") is True or r.get("decision") == "require_human_approval")
            and r.get("review_status") in ["approved", "dismissed"]
        )

        # 4. Consultar eventos de auditoría para brechas de SLA
        audit_events = await self.firestore_service.list_documents("audit_events")
        sla_breaches = sum(1 for e in audit_events if e.get("event_type") == "incident_sla_breached")

        # 5. Obtener datos de RuntimeStatsCollector
        stats = stats_collector.get_stats()
        avg_llm_latency_ms = float(stats.get("avg_latency_ms", 0.0))
        fallback_count = int(stats.get("fallbacks", 0))
        estimated_prompt_tokens = int(stats.get("prompt_tokens", 0))
        estimated_completion_tokens = int(stats.get("completion_tokens", 0))
        estimated_total_tokens = int(stats.get("total_tokens", 0))

        # 6. Estimar costos
        estimated_llm_cost_usd = CostEstimator.estimate_cost(
            estimated_prompt_tokens,
            estimated_completion_tokens,
        )

        return BusinessMetrics(
            total_conversations=total_conversations,
            incidents_created=incidents_created,
            visits_proposed=visits_proposed,
            visits_confirmed=visits_confirmed,
            gmail_drafts_proposed=gmail_drafts_proposed,
            gmail_drafts_approved=gmail_drafts_approved,
            human_reviews_required=human_reviews_required,
            human_reviews_completed=human_reviews_completed,
            fallback_count=fallback_count,
            sla_breaches=sla_breaches,
            cancelled_incidents=cancelled_incidents,
            closed_incidents=closed_incidents,
            avg_llm_latency_ms=avg_llm_latency_ms,
            estimated_prompt_tokens=estimated_prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            estimated_total_tokens=estimated_total_tokens,
            estimated_llm_cost_usd=estimated_llm_cost_usd,
        )
