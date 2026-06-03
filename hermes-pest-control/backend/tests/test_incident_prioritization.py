import pytest
from app.incidents.intake_service import IncidentIntakeService
from app.schemas.incoming_message import IncomingMessage
from app.incidents.prioritization.engine import IncidentPrioritizationEngine
from app.incidents.prioritization.contracts import IncidentSeverity, IncidentPriority
from app.pests.classifier import PestClassifier
from app.customers.classifier import CustomerTypeClassifier, CustomerType


def _incoming_message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="user-123",
        external_chat_id="chat-123",
        message_type="text",
        text=text,
        attachments=[],
        metadata={},
    )


# --- Tests Unitarios del Engine ---

def test_engine_cockroach_food_risk() -> None:
    classifier = PestClassifier()
    pest_info = classifier.classify("cucarachas")
    engine = IncidentPrioritizationEngine()

    # Cocina / Restaurante
    assessment = engine.assess(
        pest_classification=pest_info,
        location_text="cocina de restaurante",
        customer_type=CustomerType.HOSPITALITY,
        affected_area="cocina",
    )
    assert assessment.incident_severity == IncidentSeverity.HIGH
    assert assessment.incident_priority == IncidentPriority.URGENT
    assert assessment.recommended_response_hours == 24
    assert assessment.reason == "Posible riesgo alimentario."


def test_engine_cockroach_no_food_risk() -> None:
    classifier = PestClassifier()
    pest_info = classifier.classify("cucarachas")
    engine = IncidentPrioritizationEngine()

    # Sin riesgo alimentario (ej. en el jardín o salón de casa)
    assessment = engine.assess(
        pest_classification=pest_info,
        location_text="en el salón",
        customer_type=CustomerType.PRIVATE_HOME,
        affected_area="salón",
    )
    assert assessment.incident_severity == IncidentSeverity.HIGH
    assert assessment.incident_priority == IncidentPriority.HIGH
    assert assessment.recommended_response_hours == 48
    assert assessment.reason == "Presencia de cucarachas."


# --- Tests de Integración mediante Intake Service ---

@pytest.mark.asyncio
async def test_prioritization_case_1() -> None:
    # Caso 1: Tengo cucarachas en la cocina de un restaurante.
    # Esperado: HIGH URGENT 24h
    service = IncidentIntakeService()
    message = _incoming_message("Tengo cucarachas en la cocina de un restaurante.")
    state = await service.process_intake(message)

    assert state.pest_type == "COCKROACH"
    assert state.severity == IncidentSeverity.HIGH
    assert state.priority == IncidentPriority.URGENT
    assert state.response_hours == 24
    assert state.assessment_reason == "Posible riesgo alimentario."
    assert state.requires_human_review is False


@pytest.mark.asyncio
async def test_prioritization_case_2() -> None:
    # Caso 2: He visto una rata en mi bar.
    # Esperado: HIGH URGENT 24h
    service = IncidentIntakeService()
    message = _incoming_message("He visto una rata en mi bar.")
    state = await service.process_intake(message)

    assert state.pest_type == "RODENT"
    assert state.severity == IncidentSeverity.HIGH
    assert state.priority == IncidentPriority.URGENT
    assert state.response_hours == 24
    assert state.assessment_reason == "Posible riesgo sanitario."
    assert state.requires_human_review is False


@pytest.mark.asyncio
async def test_prioritization_case_3() -> None:
    # Caso 3: Tengo hormigas en la terraza de casa.
    # Esperado: LOW NORMAL 72h
    service = IncidentIntakeService()
    message = _incoming_message("Tengo hormigas en la terraza de casa.")
    state = await service.process_intake(message)

    assert state.pest_type == "ANT"
    assert state.severity == IncidentSeverity.LOW
    assert state.priority == IncidentPriority.NORMAL
    assert state.response_hours == 72
    assert state.assessment_reason == "Presencia de hormigas."
    assert state.requires_human_review is False


@pytest.mark.asyncio
async def test_prioritization_case_4() -> None:
    # Caso 4: Hay mosquitos en la comunidad.
    # Esperado: MEDIUM NORMAL 48h
    service = IncidentIntakeService()
    message = _incoming_message("Hay mosquitos en la comunidad.")
    state = await service.process_intake(message)

    assert state.pest_type == "FLYING_INSECT"
    assert state.severity == IncidentSeverity.MEDIUM
    assert state.priority == IncidentPriority.NORMAL
    assert state.response_hours == 48
    assert state.assessment_reason == "Presencia de insectos voladores."
    assert state.requires_human_review is False


@pytest.mark.asyncio
async def test_prioritization_case_5() -> None:
    # Caso 5: Tengo unos bichos raros.
    # Esperado: requires_human_review = True
    service = IncidentIntakeService()
    message = _incoming_message("Tengo unos bichos raros.")
    state = await service.process_intake(message)

    assert state.pest_type == "UNKNOWN"
    assert state.requires_human_review is True
    assert state.severity == IncidentSeverity.MEDIUM
    assert state.priority == IncidentPriority.HIGH
    assert state.assessment_reason == "Plaga desconocida que requiere revisión humana."


# --- Nuevos Tests Específicos Exigidos ---

@pytest.mark.asyncio
async def test_unknown_escalates_to_human_flow() -> None:
    # Validar que plagas UNKNOWN (bichos raros) escalen directamente a revisión humana
    from app.services.conversation_service import ConversationService
    from app.services.mock_firestore_service import MockFirestoreService

    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    service.audit_service.repository.clear()

    message = _incoming_message("Tengo unos bichos raros en la pared. Mi nombre es Carlos.")
    response = await service.handle_incoming_message(message)

    assert response.action.type == "escalate_to_human"
    assert response.incident is not None
    assert response.incident.severity == "MEDIUM"
    assert response.incident.priority == "high"  # Piso de prioridad para revisión humana es high
    assert response.incident.assessment_reason == "Plaga desconocida que requiere revisión humana."


@pytest.mark.asyncio
async def test_metadata_persisted_in_incident_draft() -> None:
    # Validar que los metadatos de priorización se guarden en metadata de IncidentDraft
    from app.services.conversation_service import ConversationService
    from app.services.mock_firestore_service import MockFirestoreService

    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    service.audit_service.repository.clear()
    message = _incoming_message("Tengo cucarachas en la cocina del local central. Mi nombre es Carlos.")

    response = await service.handle_incoming_message(message)

    assert response.action.type == "create_incident"
    assert response.incident is not None
    assert response.incident.id is not None

    # Recuperar de la base de datos simulada
    incident_in_db = await service.incident_service.get_incident(response.incident.id)
    assert incident_in_db is not None

    metadata = incident_in_db.get("metadata", {})
    assert "classification" in metadata
    assert metadata["classification"]["pest_type"] == "COCKROACH"
    assert metadata["severity"] == "HIGH"
    assert metadata["priority"] == "urgent"
    assert metadata["response_hours"] == 24
    assert metadata["assessment_reason"] == "Posible riesgo alimentario."


@pytest.mark.asyncio
async def test_audit_incident_prioritized() -> None:
    # Validar que se emita el evento de auditoría INCIDENT_PRIORITIZED con metadatos cuando hay assessment real
    from app.services.conversation_service import ConversationService
    from app.services.mock_firestore_service import MockFirestoreService
    from app.audit.contracts import AuditEventType

    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    service.audit_service.repository.clear()
    message = _incoming_message("Tengo cucarachas en la cocina del local central. Mi nombre es Carlos.")

    await service.handle_incoming_message(message)

    events = service.audit_service.list_events()
    prioritized_events = [e for e in events if e.event_type == AuditEventType.INCIDENT_PRIORITIZED]

    assert len(prioritized_events) == 1
    event = prioritized_events[0]
    assert event.metadata["severity"] == "HIGH"
    assert event.metadata["priority"] == "urgent"
    assert event.metadata["reason"] == "Posible riesgo alimentario."
    assert event.metadata["response_hours"] == 24


@pytest.mark.asyncio
async def test_audit_not_prioritized_without_assessment() -> None:
    # Validar que NO se emita el evento de auditoría INCIDENT_PRIORITIZED si no hay un assessment real de plaga
    from app.services.conversation_service import ConversationService
    from app.services.mock_firestore_service import MockFirestoreService
    from app.audit.contracts import AuditEventType

    firestore = MockFirestoreService()
    service = ConversationService(firestore_service=firestore)
    service.audit_service.repository.clear()
    message = _incoming_message("Hola, buenas tardes.")

    await service.handle_incoming_message(message)

    events = service.audit_service.list_events()
    prioritized_events = [e for e in events if e.event_type == AuditEventType.INCIDENT_PRIORITIZED]

    assert len(prioritized_events) == 0
