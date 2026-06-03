from app.pests.contracts import PestClassification
from app.customers.contracts import CustomerType
from app.incidents.prioritization.contracts import IncidentAssessment, IncidentPriority
from app.incidents.dispatch.contracts import DispatchAssessment, VisitType, TechnicianLevel, DispatchBucket


class DispatchAssessmentEngine:
    def assess(
        self,
        incident_assessment: IncidentAssessment,
        pest_classification: PestClassification | None,
        customer_type: CustomerType,
    ) -> DispatchAssessment:
        if not pest_classification or not pest_classification.pest_type:
            return DispatchAssessment(
                visit_type=VisitType.INSPECTION,
                technician_level=TechnicianLevel.JUNIOR,
                dispatch_bucket=DispatchBucket.PLANNED,
                sla_hours=72,
                reason="Sin plaga clasificada. Se requiere inspección inicial.",
            )

        pest_type = (pest_classification.pest_type or "").upper()

        # 1. Unknown / requiere revisión humana
        if pest_type == "UNKNOWN" or pest_classification.requires_human_review or incident_assessment.requires_human_review:
            return DispatchAssessment(
                visit_type=VisitType.HUMAN_REVIEW,
                technician_level=TechnicianLevel.SENIOR,
                dispatch_bucket=DispatchBucket.MANUAL_REVIEW,
                sla_hours=None,
                reason="Plaga desconocida o caso sensible que requiere revisión humana.",
            )

        # 2. Cockroach + Hospitality / Food Business (riesgo alimentario)
        if pest_type == "COCKROACH":
            is_food_risk = (
                customer_type in {CustomerType.HOSPITALITY, CustomerType.FOOD_BUSINESS}
                or incident_assessment.incident_priority == IncidentPriority.URGENT
            )
            if is_food_risk:
                return DispatchAssessment(
                    visit_type=VisitType.URGENT_TREATMENT,
                    technician_level=TechnicianLevel.STANDARD,
                    dispatch_bucket=DispatchBucket.URGENT_24H,
                    sla_hours=24,
                    reason="Tratamiento urgente de cucarachas por posible riesgo alimentario.",
                )
            else:
                return DispatchAssessment(
                    visit_type=VisitType.TREATMENT,
                    technician_level=TechnicianLevel.STANDARD,
                    dispatch_bucket=DispatchBucket.NEXT_48H,
                    sla_hours=48,
                    reason="Tratamiento de cucarachas en zona no crítica.",
                )

        # 3. Rodent
        if pest_type == "RODENT":
            return DispatchAssessment(
                visit_type=VisitType.URGENT_TREATMENT,
                technician_level=TechnicianLevel.SENIOR,
                dispatch_bucket=DispatchBucket.URGENT_24H,
                sla_hours=24,
                reason="Tratamiento urgente de roedores por riesgo sanitario.",
            )

        # 4. Ant
        if pest_type == "ANT":
            return DispatchAssessment(
                visit_type=VisitType.TREATMENT,
                technician_level=TechnicianLevel.JUNIOR,
                dispatch_bucket=DispatchBucket.THIS_WEEK,
                sla_hours=72,
                reason="Tratamiento de hormigas.",
            )

        # 5. Fallback por defecto (Flying insect, etc.)
        return DispatchAssessment(
            visit_type=VisitType.TREATMENT,
            technician_level=TechnicianLevel.STANDARD,
            dispatch_bucket=DispatchBucket.NEXT_48H,
            sla_hours=48,
            reason="Tratamiento estándar de plaga común.",
        )
