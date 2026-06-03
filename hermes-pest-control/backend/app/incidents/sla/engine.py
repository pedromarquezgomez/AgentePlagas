from datetime import datetime, timezone

from app.incidents.sla.contracts import SLAAssessment, SLAStatus
from app.incidents.sla.rules import AT_RISK_REMAINING_RATIO, COMPLETED_INCIDENT_STATUSES


class SLAEngine:
    def assess(
        self,
        *,
        incident_created_at: datetime,
        incident_status: str,
        sla_hours: int | float | None,
        current_time: datetime | None = None,
        incident_id: str | None = None,
    ) -> SLAAssessment:
        now = current_time or datetime.now(timezone.utc)
        created_at = self._ensure_timezone(incident_created_at)
        elapsed_hours = max((self._ensure_timezone(now) - created_at).total_seconds() / 3600, 0)

        if incident_status in COMPLETED_INCIDENT_STATUSES:
            return SLAAssessment(
                incident_id=incident_id,
                sla_status=SLAStatus.COMPLETED,
                elapsed_hours=elapsed_hours,
                remaining_hours=0,
                breach_hours=None,
                is_overdue=False,
                reason="Incidencia cerrada o finalizada.",
            )

        if not sla_hours or sla_hours <= 0:
            return SLAAssessment(
                incident_id=incident_id,
                sla_status=SLAStatus.ON_TRACK,
                elapsed_hours=elapsed_hours,
                remaining_hours=None,
                breach_hours=None,
                is_overdue=False,
                reason="Sin SLA definido para esta incidencia.",
            )

        remaining_hours = float(sla_hours) - elapsed_hours
        if remaining_hours < 0:
            return SLAAssessment(
                incident_id=incident_id,
                sla_status=SLAStatus.BREACHED,
                elapsed_hours=elapsed_hours,
                remaining_hours=0,
                breach_hours=abs(remaining_hours),
                is_overdue=True,
                reason="La incidencia ha superado su SLA operativo.",
            )

        at_risk_threshold = float(sla_hours) * AT_RISK_REMAINING_RATIO
        if remaining_hours <= at_risk_threshold:
            return SLAAssessment(
                incident_id=incident_id,
                sla_status=SLAStatus.AT_RISK,
                elapsed_hours=elapsed_hours,
                remaining_hours=remaining_hours,
                breach_hours=None,
                is_overdue=False,
                reason="La incidencia está dentro del último 25% de su SLA.",
            )

        return SLAAssessment(
            incident_id=incident_id,
            sla_status=SLAStatus.ON_TRACK,
            elapsed_hours=elapsed_hours,
            remaining_hours=remaining_hours,
            breach_hours=None,
            is_overdue=False,
            reason="La incidencia sigue dentro del objetivo SLA.",
        )

    def _ensure_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
