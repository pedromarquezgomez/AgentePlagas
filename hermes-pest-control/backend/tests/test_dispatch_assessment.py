from pathlib import Path

from app.customers.contracts import CustomerType
from app.incidents.dispatch.contracts import (
    DispatchBucket,
    TechnicianLevel,
    VisitType,
)
from app.incidents.dispatch.engine import DispatchAssessmentEngine
from app.incidents.prioritization.contracts import (
    IncidentAssessment,
    IncidentPriority,
    IncidentSeverity,
)
from app.pests.contracts import PestClassification


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _assessment(
    *,
    severity: IncidentSeverity = IncidentSeverity.MEDIUM,
    priority: IncidentPriority = IncidentPriority.NORMAL,
    requires_human_review: bool = False,
) -> IncidentAssessment:
    return IncidentAssessment(
        incident_severity=severity,
        incident_priority=priority,
        requires_human_review=requires_human_review,
        reason="Test assessment.",
        recommended_response_hours=48,
    )


def _pest(
    pest_type: str,
    *,
    requires_human_review: bool = False,
) -> PestClassification:
    return PestClassification(
        pest_type=pest_type,
        confidence="high",
        evidence=f"Detected {pest_type}.",
        detected_terms=[pest_type.casefold()],
        recommended_priority="high",
        requires_human_review=requires_human_review,
        pest_type_spanish=pest_type.casefold(),
    )


def test_cockroach_hospitality_requires_urgent_treatment() -> None:
    result = DispatchAssessmentEngine().assess(
        incident_assessment=_assessment(
            severity=IncidentSeverity.HIGH,
            priority=IncidentPriority.HIGH,
        ),
        pest_classification=_pest("COCKROACH"),
        customer_type=CustomerType.HOSPITALITY,
    )

    assert result.visit_type == VisitType.URGENT_TREATMENT
    assert result.technician_level == TechnicianLevel.STANDARD
    assert result.dispatch_bucket == DispatchBucket.URGENT_24H
    assert result.sla_hours == 24
    assert "riesgo alimentario" in (result.reason or "").casefold()


def test_rodent_requires_senior_urgent_treatment() -> None:
    result = DispatchAssessmentEngine().assess(
        incident_assessment=_assessment(
            severity=IncidentSeverity.HIGH,
            priority=IncidentPriority.URGENT,
        ),
        pest_classification=_pest("RODENT"),
        customer_type=CustomerType.PRIVATE_HOME,
    )

    assert result.visit_type == VisitType.URGENT_TREATMENT
    assert result.technician_level == TechnicianLevel.SENIOR
    assert result.dispatch_bucket == DispatchBucket.URGENT_24H
    assert result.sla_hours == 24


def test_ant_goes_to_this_week_junior_treatment() -> None:
    result = DispatchAssessmentEngine().assess(
        incident_assessment=_assessment(
            severity=IncidentSeverity.LOW,
            priority=IncidentPriority.LOW,
        ),
        pest_classification=_pest("ANT"),
        customer_type=CustomerType.PRIVATE_HOME,
    )

    assert result.visit_type == VisitType.TREATMENT
    assert result.technician_level == TechnicianLevel.JUNIOR
    assert result.dispatch_bucket == DispatchBucket.THIS_WEEK
    assert result.sla_hours == 72


def test_unknown_pest_requires_manual_review() -> None:
    result = DispatchAssessmentEngine().assess(
        incident_assessment=_assessment(
            severity=IncidentSeverity.MEDIUM,
            priority=IncidentPriority.NORMAL,
        ),
        pest_classification=_pest("UNKNOWN"),
        customer_type=CustomerType.UNKNOWN,
    )

    assert result.visit_type == VisitType.HUMAN_REVIEW
    assert result.technician_level == TechnicianLevel.SENIOR
    assert result.dispatch_bucket == DispatchBucket.MANUAL_REVIEW
    assert result.sla_hours is None


def test_dispatch_engine_has_no_infrastructure_dependencies() -> None:
    engine_text = (
        BACKEND_ROOT / "app" / "incidents" / "dispatch" / "engine.py"
    ).read_text()
    forbidden_fragments = [
        "Firestore",
        "get_firestore_service",
        "ConversationService",
        "ToolExecutionService",
        "Provider",
        "app.harness",
        "app.tools",
        "app.services",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in engine_text


def test_dispatch_rules_are_not_duplicated_outside_dispatch_engine() -> None:
    incidents_root = BACKEND_ROOT / "app" / "incidents"
    forbidden_rule_fragments = [
        "VisitType.",
        "TechnicianLevel.",
        "DispatchBucket.",
        "URGENT_24H",
        "NEXT_48H",
        "THIS_WEEK",
        "MANUAL_REVIEW",
    ]
    allowed_files = {
        "dispatch/contracts.py",
        "dispatch/engine.py",
        "contracts.py",
    }

    for file_path in incidents_root.rglob("*.py"):
        relative_path = file_path.relative_to(incidents_root).as_posix()
        if relative_path in allowed_files:
            continue
        text = file_path.read_text()
        for fragment in forbidden_rule_fragments:
            assert fragment not in text, f"{fragment} found in {relative_path}"
