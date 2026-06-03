from app.pests.contracts import PestClassification
from app.customers.contracts import CustomerType
from app.incidents.prioritization.contracts import IncidentAssessment, IncidentSeverity, IncidentPriority


class IncidentPrioritizationEngine:
    def assess(
        self,
        pest_classification: PestClassification | None,
        location_text: str | None,
        customer_type: CustomerType,
        affected_area: str | None,
    ) -> IncidentAssessment:
        if not pest_classification or not pest_classification.pest_type:
            return IncidentAssessment(
                incident_severity=IncidentSeverity.LOW,
                incident_priority=IncidentPriority.NORMAL,
                requires_human_review=False,
                reason="Sin plaga clasificada.",
                evidence=None,
                recommended_response_hours=72,
            )

        pest_type = pest_classification.pest_type.upper()
        evidence = pest_classification.evidence

        if pest_type == "COCKROACH":
            # Verificar si aplica a riesgo alimentario
            terms_to_check = ["cocina", "restaurante", "bar", "cafetería", "cafeteria", "hostelería", "hosteleria"]
            is_food_risk = False

            if location_text and any(t in location_text.casefold() for t in terms_to_check):
                is_food_risk = True
            if affected_area and any(t in affected_area.casefold() for t in terms_to_check):
                is_food_risk = True
            if customer_type in {CustomerType.HOSPITALITY, CustomerType.FOOD_BUSINESS}:
                is_food_risk = True

            if is_food_risk:
                return IncidentAssessment(
                    incident_severity=IncidentSeverity.HIGH,
                    incident_priority=IncidentPriority.URGENT,
                    requires_human_review=False,
                    reason="Posible riesgo alimentario.",
                    evidence=evidence,
                    recommended_response_hours=24,
                )
            else:
                return IncidentAssessment(
                    incident_severity=IncidentSeverity.HIGH,
                    incident_priority=IncidentPriority.HIGH,
                    requires_human_review=False,
                    reason="Presencia de cucarachas.",
                    evidence=evidence,
                    recommended_response_hours=48,
                )

        elif pest_type == "RODENT":
            return IncidentAssessment(
                incident_severity=IncidentSeverity.HIGH,
                incident_priority=IncidentPriority.URGENT,
                requires_human_review=False,
                reason="Posible riesgo sanitario.",
                evidence=evidence,
                recommended_response_hours=24,
            )

        elif pest_type == "ANT":
            return IncidentAssessment(
                incident_severity=IncidentSeverity.LOW,
                incident_priority=IncidentPriority.NORMAL,
                requires_human_review=False,
                reason="Presencia de hormigas.",
                evidence=evidence,
                recommended_response_hours=72,
            )

        elif pest_type == "FLYING_INSECT":
            return IncidentAssessment(
                incident_severity=IncidentSeverity.MEDIUM,
                incident_priority=IncidentPriority.NORMAL,
                requires_human_review=False,
                reason="Presencia de insectos voladores.",
                evidence=evidence,
                recommended_response_hours=48,
            )

        elif pest_type == "STORED_PRODUCT_INSECT":
            return IncidentAssessment(
                incident_severity=IncidentSeverity.MEDIUM,
                incident_priority=IncidentPriority.HIGH,
                requires_human_review=False,
                reason="Presencia de plagas en productos almacenados.",
                evidence=evidence,
                recommended_response_hours=48,
            )

        else:  # UNKNOWN u otros
            return IncidentAssessment(
                incident_severity=IncidentSeverity.MEDIUM,
                incident_priority=IncidentPriority.HIGH,
                requires_human_review=True,
                reason="Plaga desconocida que requiere revisión humana.",
                evidence=evidence,
                recommended_response_hours=48,
            )
