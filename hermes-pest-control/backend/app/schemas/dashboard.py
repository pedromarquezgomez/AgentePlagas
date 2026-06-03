from pydantic import BaseModel


class IncidentDashboardSummary(BaseModel):
    total: int
    pending_review: int
    urgent: int
    ready_for_scheduling: int
    urgent_24h: int
    human_review: int
    high_priority: int
    pending_this_week: int


class HumanReviewDashboardSummary(BaseModel):
    open: int
    urgent: int


class VisitDashboardSummary(BaseModel):
    total: int
    scheduled: int
    in_progress: int
    completed: int
    today: int
    scheduled_this_week: int


class TechnicianDashboardSummary(BaseModel):
    total: int
    active: int


class DashboardSummary(BaseModel):
    incidents: IncidentDashboardSummary
    human_review: HumanReviewDashboardSummary
    visits: VisitDashboardSummary
    technicians: TechnicianDashboardSummary
