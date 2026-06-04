from pydantic import BaseModel

class BusinessMetrics(BaseModel):
    total_conversations: int
    incidents_created: int
    visits_proposed: int
    visits_confirmed: int
    gmail_drafts_proposed: int
    gmail_drafts_approved: int
    human_reviews_required: int
    human_reviews_completed: int
    fallback_count: int
    sla_breaches: int
    cancelled_incidents: int
    closed_incidents: int
    avg_llm_latency_ms: float
    estimated_prompt_tokens: int
    estimated_completion_tokens: int
    estimated_total_tokens: int
    estimated_llm_cost_usd: float
