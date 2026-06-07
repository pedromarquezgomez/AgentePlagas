import logging
import random
from typing import Callable, Any
from uuid import uuid4

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.decision_record import DecisionRecordCreate
from app.schemas.human_review import HumanReviewItemCreate
from app.schemas.incoming_message import IncomingMessage
from app.schemas.incident import IncidentDraft
from app.schemas.pilot_gate import PilotGateResult
from app.schemas.shadow_decision_record import ShadowDecisionRecordCreate
from app.services.decision_audit_service import DecisionAuditService
from app.services.firestore_factory import get_firestore_service
from app.services.hermes_clients import default_business_context
from app.services.hermes_service import HermesService
from app.services.human_review_service import HumanReviewService
from app.services.incident_service import IncidentService
from app.services.pilot_gate import HermesPilotGate
from app.services.shadow_decision_service import ShadowDecisionService

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self,
        hermes_service: HermesService | None = None,
        incident_service: IncidentService | None = None,
        decision_audit_service: DecisionAuditService | None = None,
        human_review_service: HumanReviewService | None = None,
        shadow_decision_service: ShadowDecisionService | None = None,
        shadow_hermes_service: HermesService | None = None,
        pilot_hermes_service: HermesService | None = None,
        pilot_gate: HermesPilotGate | None = None,
        firestore_service=None,
        settings: Settings | None = None,
        random_func: Callable[[], float] | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.firestore_service = (
            firestore_service
            or getattr(incident_service, "firestore_service", None)
            or get_firestore_service()
        )
        if hermes_service is None:
            from app.context.manager import ContextManager
            from app.policies.engine import PolicyEngine
            policy_engine = PolicyEngine()
            ctx_manager = ContextManager(
                firestore_service=self.firestore_service,
                policy_engine=policy_engine,
                settings=self.settings,
            )
            self.hermes_service = HermesService(
                settings=self.settings,
                context_manager=ctx_manager,
            )
        else:
            self.hermes_service = hermes_service
        self.incident_service = incident_service or IncidentService(self.firestore_service)
        self.decision_audit_service = decision_audit_service or DecisionAuditService(
            self.firestore_service
        )
        self.human_review_service = human_review_service or HumanReviewService(
            self.firestore_service
        )
        self.shadow_decision_service = shadow_decision_service or ShadowDecisionService(
            self.firestore_service
        )
        self.shadow_hermes_service = shadow_hermes_service
        self.pilot_hermes_service = pilot_hermes_service
        self.pilot_gate = pilot_gate or HermesPilotGate()
        self.random_func = random_func or random.random

        from app.services.tool_execution_service import ToolExecutionService
        from app.policies.engine import PolicyEngine
        from app.audit.service import default_audit_service

        self.tool_execution_service = ToolExecutionService(self.firestore_service)
        self.policy_engine = PolicyEngine()
        self.audit_service = default_audit_service()

    async def handle_incoming_message(self, message: IncomingMessage) -> AgentResponse:
        trace_id = self.build_trace_id()
        conversation_id = self.build_conversation_id(message)
        logger.info(
            "conversation_started trace_id=%s channel=%s conversation_id=%s",
            trace_id,
            message.channel,
            conversation_id,
        )
        import datetime
        existing_conv = await self.firestore_service.get_document("conversations", conversation_id)
        conv_state = {"phase": "IDLE"}
        if existing_conv and "conversation_state" in existing_conv:
            conv_state = existing_conv["conversation_state"]

        if conv_state.get("phase") == "DIAGNOSIS":
            diagnosis_data = conv_state.get("diagnosis", {})
            updated_at_str = diagnosis_data.get("updated_at")
            if updated_at_str:
                try:
                    updated_at = datetime.datetime.fromisoformat(updated_at_str)
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - updated_at).total_seconds() > 30 * 60:
                        conv_state = {"phase": "IDLE"}
                except Exception as exc:
                    logger.warning("Error parseando diagnosis updated_at, reseteando fase: %s", exc)
                    conv_state = {"phase": "IDLE"}

        await self._upsert_conversation_with_state(message, conversation_id, conv_state)
        inbound_message = await self._store_inbound_message(
            message,
            conversation_id,
            trace_id,
        )

        response = None

        # 1. Build context
        from app.context.customer_context_builder import CustomerContextBuilder
        context_builder = CustomerContextBuilder(
            customer_service=getattr(self, "customer_service", None),
            incident_service=self.incident_service
        )
        customer_context = await context_builder.build(message)

        # 2. Classify intent
        from app.conversation.intent_classifier import IntentClassifier, IntentType
        intent_classifier = IntentClassifier()

        # Obtener textos de usuario en el flujo actual para una clasificación de intención robusta
        from app.context.builders.history_builder import HistoryBuilder
        history_builder = HistoryBuilder(self.firestore_service)
        history_msgs = await history_builder.build(conversation_id, None)
        all_msgs = list(history_msgs) if history_msgs else []
        current_text = message.text or ""
        has_current = any(msg.get("content") == current_text for msg in all_msgs)
        if not has_current:
            all_msgs.append({"role": "user", "content": current_text})

        # Calcular cutoff
        cutoff_idx = -1
        for idx, msg in enumerate(all_msgs):
            role = msg.get("role")
            text_val = (msg.get("content") or "").casefold()
            if role in ("assistant", "outbound", "bot"):
                is_success = False
                if any(term in text_val for term in ["he registrado", "he dejado el caso", "voy a pasar este caso", "registrado por el equipo", "incidencia registrada", "aviso registrado", "caso registrado"]):
                    if "para registrar" not in text_val and "necesito" not in text_val:
                        is_success = True
                if is_success:
                    cutoff_idx = idx

        user_texts_flow = []
        for msg in all_msgs[cutoff_idx + 1:]:
            if msg.get("role") == "user":
                user_texts_flow.append(msg.get("content") or "")

        combined_user_text = " ".join(user_texts_flow) if user_texts_flow else current_text
        intent = intent_classifier.classify(combined_user_text)

        from app.incidents.status_service import IncidentStatusService
        status_service = IncidentStatusService(self.firestore_service)
        if intent == IntentType.STATUS_CHECK or status_service.is_status_query(message.text):
            status_message = await status_service.resolve_status_message(conversation_id)
            if status_message:
                response = AgentResponse(
                    reply=status_message,
                    action={"type": "collect_missing_data", "missing_fields": []},
                )

        # Check if the user is selecting a visit slot
        if response is None:
            from app.calendar.selection_service import VisitSlotSelectionService
            selection_service = VisitSlotSelectionService(self.firestore_service)
            active_proposal = await selection_service.locate_active_proposal(conversation_id)
            if active_proposal:
                slot_index = selection_service.interpret_selection(message.text)
                if slot_index is not None:
                    selected_slot = await selection_service.resolve_selection(conversation_id, message.text)
                    if selected_slot:
                        from datetime import datetime, timezone
                        approved_payload = active_proposal.get("approved_payload") or {}
                        approved_payload["selected_slot"] = {
                            "slot_index": selected_slot.slot_index,
                            "start_time": selected_slot.start_time,
                            "end_time": selected_slot.end_time,
                        }
                        approved_payload["selected_at"] = datetime.now(timezone.utc).isoformat()
                        approved_payload["customer_confirmation"] = message.text

                        await self.firestore_service.update_document(
                            "tool_execution_records",
                            active_proposal["id"],
                            {"approved_payload": approved_payload},
                        )

                        from app.audit.contracts import AuditEvent, AuditEventType
                        self.audit_service.record_event(
                            AuditEvent(
                                event_type=AuditEventType.VISIT_SLOT_SELECTED,
                                execution_id=active_proposal["id"],
                                tool_name="schedule_visit_tool",
                                provider="calendar",
                                user_id=message.external_user_id,
                                channel=message.channel,
                                status="completed",
                                message=f"Visit slot {selected_slot.slot_index} selected by customer.",
                                metadata={
                                    "incident_id": approved_payload.get("incident_id"),
                                    "slot_index": selected_slot.slot_index,
                                    "start_time": selected_slot.start_time,
                                    "end_time": selected_slot.end_time,
                                }
                            )
                        )

                        response = AgentResponse(
                            reply="Perfecto. He registrado tu preferencia de visita. Nuestro equipo revisará la disponibilidad y confirmará la cita antes de programarla definitivamente.",
                            action={"type": "schedule_visit_selection", "missing_fields": []},
                        )
                else:
                    text_lower = (message.text or "").lower()
                    option_keywords = ["opción", "opcion", "primera", "segunda", "tercera", "primer", "segundo", "tercer", "horario"]
                    if any(kw in text_lower for kw in option_keywords):
                        response = AgentResponse(
                            reply="Lo siento, no he entendido cuál de las opciones de visita prefieres. ¿Podrías indicarme si prefieres la primera, segunda o tercera opción?",
                            action={"type": "collect_missing_data", "missing_fields": []},
                        )

        if response is None:
            from app.diagnostics.diagnostic_engine import DiagnosticEngine
            from app.diagnostics.question_generator import QuestionGenerator
            from app.diagnostics.contracts import DiagnosisState

            diag_engine = DiagnosticEngine()
            q_gen = QuestionGenerator()

            # Realizar diagnóstico
            assessment_context = {
                "customer_context": customer_context,
                "history": all_msgs,
                "channel": message.channel,
                "external_user_id": message.external_user_id,
                "conversation_id": conversation_id,
                "message": message
            }
            assessment = await diag_engine.assess(message.text or "", context=assessment_context, conversation_state=conv_state)

            if assessment.state == DiagnosisState.OUT_OF_DOMAIN:
                from app.config.agent_loader import AgentConfigLoader
                loader = AgentConfigLoader()
                templates = loader.load_response_templates()
                reply = templates.get("out_of_domain", {}).get("default", {}).get("es", "No relaciono esa información con una incidencia de plagas. Si quieres, dime qué insecto, animal o señal has observado.")

                response = AgentResponse(
                    reply=reply,
                    action={"type": "out_of_domain", "missing_fields": []},
                    incident=None
                )
                conv_state = {"phase": "IDLE"}
                await self._upsert_conversation_with_state(message, conversation_id, conv_state)
                await self._store_outbound_message(message, conversation_id, trace_id, response)

                decision_record = await self._record_decision(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    message_id=inbound_message.get("id") if 'inbound_message' in locals() else None,
                    incident_id=None,
                    response=response,
                )
                await self._create_human_review_item_if_needed(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=None,
                    decision_record_id=decision_record.id if decision_record else None,
                    response=response,
                )
                return response

            elif assessment.state == DiagnosisState.DIAGNOSIS:
                reply = q_gen.generate_question(assessment)
                hypotheses_labels = [h.label for h in assessment.hypotheses]

                conv_state = {
                    "phase": "DIAGNOSIS",
                    "diagnosis": {
                        "knowledge_key": assessment.knowledge_key,
                        "hypotheses": hypotheses_labels,
                        "last_questions": [reply],
                        "evidence": assessment.hypotheses[0].evidence if assessment.hypotheses else [],
                        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                }

                response = AgentResponse(
                    reply=reply,
                    action={"type": "technical_diagnosis", "missing_fields": []},
                    incident=None
                )
                await self._upsert_conversation_with_state(message, conversation_id, conv_state)
                await self._store_outbound_message(message, conversation_id, trace_id, response)

                decision_record = await self._record_decision(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    message_id=inbound_message.get("id") if 'inbound_message' in locals() else None,
                    incident_id=None,
                    response=response,
                )
                await self._create_human_review_item_if_needed(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=None,
                    decision_record_id=decision_record.id if decision_record else None,
                    response=response,
                )
                return response

            elif assessment.state == DiagnosisState.DISCOVERY:
                import datetime
                discovery_data = assessment.discovery_data
                
                # Guardar timestamp
                discovery_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
                # Guardar en conv_state
                conv_state["phase"] = "DISCOVERY"
                conv_state["discovery"] = discovery_data
                
                await self._upsert_conversation_with_state(message, conversation_id, conv_state)
                
                response = await self._get_hermes_response(
                    message,
                    conversation_id,
                    trace_id,
                    customer_context=customer_context,
                    intent=intent,
                    conversation_state=conv_state,
                    injected_pest=discovery_data.get("knowledge_key"),
                    assessment=assessment,
                )
                
                if (not getattr(assessment, "operational_readiness", False) or response.action.type == "technical_discovery") and response.action.type not in {"escalate_to_human", "create_incident"}:
                    await self._store_outbound_message(message, conversation_id, trace_id, response)
                    
                    decision_record = await self._record_decision(
                        message=message,
                        conversation_id=conversation_id,
                        trace_id=trace_id,
                        message_id=inbound_message.get("id") if 'inbound_message' in locals() else None,
                        incident_id=None,
                        response=response,
                    )
                    await self._create_human_review_item_if_needed(
                        message=message,
                        conversation_id=conversation_id,
                        trace_id=trace_id,
                        incident_id=None,
                        decision_record_id=decision_record.id if decision_record else None,
                        response=response,
                    )
                    return response
                else:
                    conv_state["phase"] = "INTAKE"
                    # Asegurar que no se pierdan datos de discovery
                    conv_state["discovery"] = discovery_data
                    await self._upsert_conversation_with_state(message, conversation_id, conv_state)

                    # Obtener respuesta final de INTAKE
                    response = await self._get_hermes_response(
                        message,
                        conversation_id,
                        trace_id,
                        customer_context=customer_context,
                        intent=intent,
                        conversation_state=conv_state,
                        injected_pest=discovery_data.get("knowledge_key"),
                        assessment=assessment,
                    )

            else:
                # Transición a INTAKE
                injected_pest = None
                if conv_state.get("phase") == "DIAGNOSIS":
                    diag_data = conv_state.get("diagnosis", {})
                    if diag_data.get("knowledge_key") == "plant_pests":
                        injected_pest = "pulgón verde"
                elif conv_state.get("phase") == "DISCOVERY":
                    disc_data = conv_state.get("discovery", {})
                    k_key = disc_data.get("knowledge_key")
                    spanish_map = {
                        "cockroaches": "cucarachas",
                        "rodents": "roedores",
                        "ants": "hormigas",
                        "wasps": "avispas"
                    }
                    injected_pest = spanish_map.get(k_key, "cucarachas")

                conv_state = {"phase": "INTAKE"}
                if assessment.discovery_data:
                    conv_state["discovery"] = assessment.discovery_data
                await self._upsert_conversation_with_state(message, conversation_id, conv_state)

                response = await self._get_hermes_response(
                    message,
                    conversation_id,
                    trace_id,
                    customer_context=customer_context,
                    intent=intent,
                    conversation_state=conv_state,
                    injected_pest=injected_pest,
                    assessment=assessment,
                )

        if response.incident and (response.action.type == "create_incident" or self._should_create_incident(response)):
            self._enrich_incident_operational_fields(message, response.incident)
        incident_id = None

        if response.action.type == "create_incident":
            incident_id = await self._execute_create_incident_tool(
                message=message,
                conversation_id=conversation_id,
                trace_id=trace_id,
                response=response,
                customer_context=customer_context,
                intent=intent
            )
            if incident_id:
                await self._propose_gmail_draft_tool(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=incident_id,
                    response=response,
                )
                await self._propose_schedule_visit_tool(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=incident_id,
                    response=response,
                )
        elif self._should_create_incident(response):
            incident = self._build_incident(message, conversation_id, response, customer_context, intent)
            created_incident = await self.incident_service.create_incident(incident)
            incident_id = created_incident.id
            if response.incident is not None:
                response.incident.id = created_incident.id
                response.incident.conversation_id = created_incident.conversation_id
                response.incident.status = created_incident.status
            if incident_id:
                await self._propose_gmail_draft_tool(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=incident_id,
                    response=response,
                )
                await self._propose_schedule_visit_tool(
                    message=message,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    incident_id=incident_id,
                    response=response,
                )

        decision_record = await self._record_decision(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            message_id=inbound_message.get("id"),
            incident_id=incident_id,
            response=response,
        )
        await self._create_human_review_item_if_needed(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            incident_id=incident_id,
            decision_record_id=decision_record.id,
            response=response,
        )
        await self._run_shadow_if_enabled(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            primary_response=response,
        )
        # Registrar evento de priorización en auditoría al final si existe assessment real
        if response.incident and response.incident.severity:
            from app.audit.contracts import AuditEvent, AuditEventType
            self.audit_service.record_event(
                AuditEvent(
                    event_type=AuditEventType.INCIDENT_PRIORITIZED,
                    execution_id=trace_id,
                    user_id=message.external_user_id,
                    channel=message.channel,
                    status="completed",
                    message="Incident prioritization completed.",
                    metadata={
                        "severity": response.incident.severity,
                        "priority": response.incident.priority,
                        "reason": response.incident.assessment_reason,
                        "response_hours": response.incident.response_hours,
                    },
                )
            )

        await self._store_outbound_message(message, conversation_id, trace_id, response)

        logger.info(
            "conversation_completed trace_id=%s conversation_id=%s action_type=%s",
            trace_id,
            conversation_id,
            response.action.type,
        )
        return response

    def _enrich_incident_operational_fields(
        self,
        message: IncomingMessage,
        incident_data: Any,
    ) -> None:
        if not incident_data:
            return

        from app.pests.classifier import PestClassifier
        from app.customers.classifier import CustomerTypeClassifier
        from app.incidents.prioritization.engine import IncidentPrioritizationEngine
        from app.incidents.dispatch.engine import DispatchAssessmentEngine
        from app.pests.contracts import PestClassification

        pest_classifier = PestClassifier()
        customer_classifier = CustomerTypeClassifier()
        prioritization_engine = IncidentPrioritizationEngine()
        dispatch_engine = DispatchAssessmentEngine()

        text = message.text or ""
        customer_type = customer_classifier.classify(text)

        existing_pest = getattr(incident_data, "pest_type", None)
        if existing_pest:
            spanish_map = {
                "cucarachas": "COCKROACH",
                "roedores": "RODENT",
                "hormigas": "ANT",
                "insectos voladores": "FLYING_INSECT",
                "insectos de productos almacenados": "STORED_PRODUCT_INSECT",
            }
            mapped_pest = existing_pest
            if existing_pest.casefold() in spanish_map:
                mapped_pest = spanish_map[existing_pest.casefold()]
            pest_classification = PestClassification(
                pest_type=mapped_pest.upper(),
                confidence=getattr(incident_data, "confidence", None) or "high",
                evidence=getattr(incident_data, "evidence", None) or "Enriched from existing proposal",
                detected_terms=getattr(incident_data, "detected_terms", []) or [existing_pest.casefold()],
                recommended_priority=getattr(incident_data, "priority", None) or "high",
                requires_human_review=False,
                pest_type_spanish=existing_pest if existing_pest.casefold() in spanish_map else None,
            )
        else:
            pest_classification = pest_classifier.classify(text)

        location = incident_data.location or ""
        affected_area = incident_data.affected_area or ""

        assessment = prioritization_engine.assess(
            pest_classification=pest_classification,
            location_text=location,
            customer_type=customer_type,
            affected_area=affected_area,
        )

        dispatch_assessment = dispatch_engine.assess(
            incident_assessment=assessment,
            pest_classification=pest_classification,
            customer_type=customer_type,
        )

        if not getattr(incident_data, "pest_type", None):
            incident_data.pest_type = pest_classification.pest_type

        incident_data.confidence = pest_classification.confidence
        incident_data.evidence = pest_classification.evidence
        incident_data.detected_terms = pest_classification.detected_terms or []
        incident_data.severity = assessment.incident_severity.value if hasattr(assessment.incident_severity, "value") else assessment.incident_severity
        incident_data.response_hours = assessment.recommended_response_hours
        incident_data.assessment_reason = assessment.reason

        visit_type_val = dispatch_assessment.visit_type.value if hasattr(dispatch_assessment.visit_type, "value") else dispatch_assessment.visit_type
        incident_data.visit_type = visit_type_val

        technician_level_val = dispatch_assessment.technician_level.value if hasattr(dispatch_assessment.technician_level, "value") else dispatch_assessment.technician_level
        incident_data.technician_level = technician_level_val

        dispatch_bucket_val = dispatch_assessment.dispatch_bucket.value if hasattr(dispatch_assessment.dispatch_bucket, "value") else dispatch_assessment.dispatch_bucket
        incident_data.dispatch_bucket = dispatch_bucket_val

        incident_data.sla_hours = dispatch_assessment.sla_hours

        if assessment.incident_priority:
            from app.incidents.prioritization.contracts import IncidentPriority
            priority_map = {
                IncidentPriority.URGENT: "urgent",
                IncidentPriority.HIGH: "high",
                IncidentPriority.NORMAL: "medium",
                IncidentPriority.LOW: "low",
            }
            incident_data.priority = priority_map.get(assessment.incident_priority, incident_data.priority)

    async def _propose_gmail_draft_tool(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        incident_id: str,
        response: AgentResponse,
    ) -> None:
        import re
        from uuid import uuid4
        from app.schemas.tool_harness import ToolExecutionRecord
        from app.policies.contracts import PolicyContext, PolicyDecision
        from app.audit.contracts import AuditEvent, AuditEventType
        from app.incidents.intake_service import IncidentIntakeService

        text = message.text or ""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if not email_match:
            return

        email_address = email_match.group(0)
        customer_name = IncidentIntakeService()._extract_customer_name(text) or "Pedro"

        pest_spanish_map = {
            "COCKROACH": "cucarachas",
            "RODENT": "roedores",
            "ANT": "hormigas",
            "FLYING_INSECT": "insectos voladores",
            "STORED_PRODUCT_INSECT": "insectos de productos almacenados",
            "UNKNOWN": "plagas no identificadas",
        }
        pest_spanish = pest_spanish_map.get(response.incident.pest_type, "cucarachas")

        priority_spanish_map = {
            "urgent": "urgente",
            "high": "alta",
            "medium": "media",
            "low": "baja",
        }
        priority_spanish = priority_spanish_map.get(response.incident.priority.lower(), "urgente")

        sla_hours = response.incident.sla_hours or 24
        sla_spanish = f"{sla_hours} horas"

        visit_type_map = {
            "URGENT_TREATMENT": "tratamiento urgente",
            "TREATMENT": "tratamiento",
            "INSPECTION": "inspección",
            "FOLLOW_UP": "seguimiento",
            "HUMAN_REVIEW": "revisión humana",
        }
        visit_type_str = response.incident.visit_type
        if hasattr(visit_type_str, "value"):
            visit_type_str = visit_type_str.value
        actuation_spanish = visit_type_map.get(str(visit_type_str).upper(), "tratamiento urgente")

        location = response.incident.location or "Calle Larios 5, Málaga"
        affected_area = response.incident.affected_area or "cocina"

        body = (
            f"Hola {customer_name},\n\n"
            "Hemos registrado tu incidencia.\n\n"
            f"Tipo de plaga: {pest_spanish}\n"
            f"Ubicación: {location}\n"
            f"Zona afectada: {affected_area}\n"
            f"Prioridad: {priority_spanish}\n"
            f"SLA recomendado: {sla_spanish}\n"
            f"Tipo de actuación recomendada: {actuation_spanish}\n\n"
            "Un técnico revisará la información y confirmará los próximos pasos.\n\n"
            "Un saludo."
        )

        tool_name = "gmail.create_draft"
        tool_request_id = str(uuid4())
        tool_decision_id = str(uuid4())
        execution_id = str(uuid4())

        tool_payload = {
            "recipient": email_address,
            "subject": "Incidencia registrada — control de plagas",
            "body": body,
        }

        # Record proposed tool event in AuditService
        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.TOOL_PROPOSED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="gmail",
                user_id=message.external_user_id,
                channel=message.channel,
                status="requested",
                message="Tool execution requested.",
                metadata={
                    "action": "create_draft",
                    "risk_level": 1,
                    "requires_approval": True,
                },
            )
        )

        policy_context = PolicyContext(
            channel=message.channel,
            user_id=message.external_user_id,
            requested_tool=tool_name,
            requested_action="create_draft",
            source_provider="gmail",
            incident_id=incident_id,
        )
        policy_result = self.policy_engine.evaluate(policy_context)

        # Record policy evaluation in AuditService
        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.POLICY_EVALUATED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="gmail",
                user_id=message.external_user_id,
                channel=message.channel,
                policy_decision=policy_result.decision.value,
                status=policy_result.decision.value,
                message="Policy Engine evaluated tool execution.",
                metadata={"action": "create_draft"},
            )
        )

        # Record human review required in AuditService
        if policy_result.decision == PolicyDecision.REQUIRE_HUMAN_REVIEW:
            self.audit_service.record_event(
                AuditEvent(
                    event_type=AuditEventType.HUMAN_REVIEW_REQUIRED,
                    execution_id=execution_id,
                    tool_name=tool_name,
                    provider="gmail",
                    user_id=message.external_user_id,
                    channel=message.channel,
                    policy_decision=policy_result.decision.value,
                    status="requires_human_review",
                    message="Policy requires human review before tool execution.",
                    metadata={"action": "create_draft"},
                )
            )

        decision_outcome = "require_human_approval"
        execution_status = "pending_human_approval"
        review_status = "proposed"
        requires_approval = True

        if policy_result.decision == PolicyDecision.ALLOW:
            decision_outcome = "allow"
            execution_status = "allowed_not_executed"
            review_status = "approved"
            requires_approval = False
        elif policy_result.decision == PolicyDecision.DENY:
            decision_outcome = "deny"
            execution_status = "blocked"
            review_status = "dismissed"
            requires_approval = False

        record = ToolExecutionRecord(
            id=execution_id,
            tool_request_id=tool_request_id,
            tool_decision_id=tool_decision_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            provider="gmail",
            action="create_draft",
            risk_level=1,
            requires_approval=requires_approval,
            decision=decision_outcome,
            execution_status=execution_status,
            review_status=review_status,
            approved_payload=tool_payload,
            metadata={"payload": tool_payload},
        )
        await self.tool_execution_service.create_execution_record(record)

    async def _propose_schedule_visit_tool(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        incident_id: str,
        response: AgentResponse,
    ) -> None:
        import re
        from uuid import uuid4
        from datetime import datetime, timedelta, timezone
        from app.schemas.tool_harness import ToolExecutionRecord
        from app.policies.contracts import PolicyContext, PolicyDecision
        from app.audit.contracts import AuditEvent, AuditEventType
        from app.incidents.intake_service import IncidentIntakeService
        from app.calendar.calendar_service import HermesCalendarService
        from app.calendar.availability_service import AvailabilityService

        text = message.text or ""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        customer_email = email_match.group(0) if email_match else None
        customer_name = IncidentIntakeService()._extract_customer_name(text) or "Pedro"

        location = response.incident.location or "Calle Larios 5, Málaga"
        visit_type = response.incident.visit_type
        if hasattr(visit_type, "value"):
            visit_type = visit_type.value
        visit_type_str = str(visit_type or "TREATMENT")

        # 1. Obtener slots ocupados
        calendar_service = HermesCalendarService()
        now = datetime.now(timezone.utc)
        start_date = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        end_date = start_date + timedelta(days=14)

        try:
            busy_slots = await calendar_service.get_busy_slots(start_date.isoformat(), end_date.isoformat())
        except Exception as exc:
            logger.warning("Error getting busy slots, falling back to empty: %s", exc)
            busy_slots = []

        # 2. Calcular slots libres
        proposed_slots = AvailabilityService.calculate_free_slots(
            busy_slots=busy_slots,
            start_date=start_date,
            duration_minutes=60,
            max_slots=3,
        )

        tool_name = "schedule_visit_tool"
        tool_request_id = str(uuid4())
        tool_decision_id = str(uuid4())
        execution_id = str(uuid4())

        tool_payload = {
            "incident_id": incident_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "location": location,
            "visit_type": visit_type_str,
            "pest_type": response.incident.pest_type if response.incident else "COCKROACH",
            "duration_minutes": 60,
            "proposed_slots": proposed_slots,
            "selected_slot": proposed_slots[0] if proposed_slots else None,
        }

        # Registrar propuesta en la auditoría
        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.TOOL_PROPOSED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="calendar",
                user_id=message.external_user_id,
                channel=message.channel,
                status="requested",
                message="Tool execution requested.",
                metadata={
                    "action": "schedule_visit",
                    "risk_level": 3,
                    "requires_approval": True,
                },
            )
        )

        # Evaluar la política
        policy_context = PolicyContext(
            channel=message.channel,
            user_id=message.external_user_id,
            requested_tool=tool_name,
            requested_action="schedule_visit",
            source_provider="calendar",
            incident_id=incident_id,
        )
        policy_result = self.policy_engine.evaluate(policy_context)

        # Registrar la evaluación en auditoría
        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.POLICY_EVALUATED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="calendar",
                user_id=message.external_user_id,
                channel=message.channel,
                policy_decision=policy_result.decision.value,
                status=policy_result.decision.value,
                message="Policy Engine evaluated tool execution.",
                metadata={"action": "schedule_visit"},
            )
        )

        # Registrar si requiere revisión humana
        if policy_result.decision == PolicyDecision.REQUIRE_HUMAN_REVIEW:
            self.audit_service.record_event(
                AuditEvent(
                    event_type=AuditEventType.HUMAN_REVIEW_REQUIRED,
                    execution_id=execution_id,
                    tool_name=tool_name,
                    provider="calendar",
                    user_id=message.external_user_id,
                    channel=message.channel,
                    policy_decision=policy_result.decision.value,
                    status="requires_human_review",
                    message="Policy requires human review before tool execution.",
                    metadata={"action": "schedule_visit"},
                )
            )

        decision_outcome = "require_human_approval"
        execution_status = "pending_human_approval"
        review_status = "proposed"
        requires_approval = True

        if policy_result.decision == PolicyDecision.ALLOW:
            decision_outcome = "allow"
            execution_status = "allowed_not_executed"
            review_status = "approved"
            requires_approval = False
        elif policy_result.decision == PolicyDecision.DENY:
            decision_outcome = "deny"
            execution_status = "blocked"
            review_status = "dismissed"
            requires_approval = False

        record = ToolExecutionRecord(
            id=execution_id,
            tool_request_id=tool_request_id,
            tool_decision_id=tool_decision_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            provider="calendar",
            action="schedule_visit",
            risk_level=3,
            requires_approval=requires_approval,
            decision=decision_outcome,
            execution_status=execution_status,
            review_status=review_status,
            approved_payload=tool_payload,
            metadata={"payload": tool_payload},
        )
        await self.tool_execution_service.create_execution_record(record)

    async def _execute_create_incident_tool(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        response: AgentResponse,
        customer_context: Any = None,
        intent: Any = None,
    ) -> str | None:
        from app.schemas.tool_harness import ToolExecutionRecord
        from app.policies.contracts import PolicyContext, PolicyDecision
        from app.audit.contracts import AuditEvent, AuditEventType

        tool_name = "create_incident_tool"
        tool_request_id = str(uuid4())
        tool_decision_id = str(uuid4())
        execution_id = str(uuid4())

        tool_payload = {
            "conversation_id": conversation_id,
            "channel": message.channel,
            "pest_type": response.incident.pest_type if response.incident else None,
            "location": response.incident.location if response.incident else None,
            "affected_area": response.incident.affected_area if response.incident else None,
            "priority": response.incident.priority if response.incident else "medium",
            "summary": response.incident.summary if response.incident else None,
            "confidence": getattr(response.incident, "confidence", None) if response.incident else None,
            "severity": getattr(response.incident, "severity", None) if response.incident else None,
            "operational_priority": self._operational_priority_from_incident(response.incident) if response.incident else None,
            "response_hours": getattr(response.incident, "response_hours", None) if response.incident else None,
            "assessment_reason": getattr(response.incident, "assessment_reason", None) if response.incident else None,
            "visit_type": getattr(response.incident, "visit_type", None) if response.incident else None,
            "technician_level": getattr(response.incident, "technician_level", None) if response.incident else None,
            "dispatch_bucket": getattr(response.incident, "dispatch_bucket", None) if response.incident else None,
            "sla_hours": getattr(response.incident, "sla_hours", None) if response.incident else None,
            "metadata": {
                "customer_name": response.metadata.get("customer_name")
                or (getattr(response.incident, "metadata", {}) or {}).get("customer_name")
                if response.incident else None,
                "confidence": getattr(response.incident, "confidence", None) if response.incident else None,
                "evidence": getattr(response.incident, "evidence", None) if response.incident else None,
                "detected_terms": getattr(response.incident, "detected_terms", []) if response.incident else [],
                "severity": getattr(response.incident, "severity", None) if response.incident else None,
                "priority": getattr(response.incident, "priority", None) if response.incident else None,
                "response_hours": getattr(response.incident, "response_hours", None) if response.incident else None,
                "assessment_reason": getattr(response.incident, "assessment_reason", None) if response.incident else None,
                "visit_type": getattr(response.incident, "visit_type", None) if response.incident else None,
                "technician_level": getattr(response.incident, "technician_level", None) if response.incident else None,
                "dispatch_bucket": getattr(response.incident, "dispatch_bucket", None) if response.incident else None,
                "sla_hours": getattr(response.incident, "sla_hours", None) if response.incident else None,
                "classification": {
                    "pest_type": response.incident.pest_type if response.incident else None,
                    "confidence": getattr(response.incident, "confidence", None) if response.incident else None,
                    "evidence": getattr(response.incident, "evidence", None) if response.incident else None,
                    "detected_terms": getattr(response.incident, "detected_terms", []) if response.incident else [],
                } if response.incident else None,
                "customer_id": customer_context.customer_id if customer_context else None,
                "is_recurrence": intent.value == "RECURRENCE" if intent else False,
                "parent_incident_id": customer_context.last_incident_id if customer_context and intent and intent.value == "RECURRENCE" else None,
                **(response.metadata if response.metadata else {}),
            }
        }

        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.TOOL_PROPOSED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="mock_provider",
                user_id=message.external_user_id,
                channel=message.channel,
                status="requested",
                message="Tool execution requested.",
                metadata={
                    "action": "create_incident",
                    "risk_level": 2,
                    "requires_approval": False,
                },
            )
        )

        policy_context = PolicyContext(
            channel=message.channel,
            user_id=message.external_user_id,
            requested_tool=tool_name,
            requested_action="create_incident",
            source_provider="mock_provider",
        )
        policy_result = self.policy_engine.evaluate(policy_context)

        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.POLICY_EVALUATED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="mock_provider",
                user_id=message.external_user_id,
                channel=message.channel,
                policy_decision=policy_result.decision.value,
                status=policy_result.decision.value,
                message="Policy Engine evaluated tool execution.",
                metadata={"action": "create_incident"},
            )
        )

        record = ToolExecutionRecord(
            id=execution_id,
            tool_request_id=tool_request_id,
            tool_decision_id=tool_decision_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            provider="mock_provider",
            action="create_incident",
            risk_level=2,
            requires_approval=False,
            decision="allow" if policy_result.decision == PolicyDecision.ALLOW else "deny",
            execution_status="allowed_not_executed" if policy_result.decision == PolicyDecision.ALLOW else "blocked",
            review_status="approved" if policy_result.decision == PolicyDecision.ALLOW else "dismissed",
            approved_payload=tool_payload,
            metadata={"payload": tool_payload},
        )
        await self.tool_execution_service.create_execution_record(record)

        incident_id = None
        if policy_result.decision == PolicyDecision.ALLOW:
            execute_fn = getattr(self.tool_execution_service, "execute_execution_record")
            execution_record = await execute_fn(execution_id)
            created_incident_data = execution_record.get("execution_result")
            if created_incident_data:
                incident_id = created_incident_data.get("id")
                if response.incident is not None:
                    response.incident.id = incident_id
                    response.incident.conversation_id = conversation_id
                    response.incident.status = created_incident_data.get("status")
        return incident_id

    def build_conversation_id(self, message: IncomingMessage) -> str:
        return f"{message.channel}:{message.external_user_id}"

    def build_trace_id(self) -> str:
        return str(uuid4())

    def _should_create_incident(self, response: AgentResponse) -> bool:
        return (
            response.action.type in {"create_incident", "escalate_to_human"}
            and bool(response.incident)
            and response.incident.should_create
        )

    def _build_incident(
        self,
        message: IncomingMessage,
        conversation_id: str,
        response: AgentResponse,
        customer_context: Any = None,
        intent: Any = None,
    ) -> IncidentDraft:
        incident_data = response.incident

        metadata = {
            "external_user_id": message.external_user_id,
            "external_chat_id": message.external_chat_id,
            "source_message_type": message.message_type,
            "source_metadata": message.metadata,
        }
        if customer_context:
            metadata["customer_id"] = customer_context.customer_id
            if intent and intent.value == "RECURRENCE":
                metadata["is_recurrence"] = True
                metadata["parent_incident_id"] = customer_context.last_incident_id
        if incident_data:
            if getattr(incident_data, "confidence", None):
                metadata["confidence"] = incident_data.confidence
            if getattr(incident_data, "evidence", None):
                metadata["evidence"] = incident_data.evidence
            if getattr(incident_data, "detected_terms", None):
                metadata["detected_terms"] = incident_data.detected_terms
            if getattr(incident_data, "severity", None):
                metadata["severity"] = incident_data.severity
            if getattr(incident_data, "response_hours", None):
                metadata["response_hours"] = incident_data.response_hours
            if getattr(incident_data, "assessment_reason", None):
                metadata["assessment_reason"] = incident_data.assessment_reason
            if getattr(incident_data, "visit_type", None):
                metadata["visit_type"] = incident_data.visit_type
            if getattr(incident_data, "technician_level", None):
                metadata["technician_level"] = incident_data.technician_level
            if getattr(incident_data, "dispatch_bucket", None):
                metadata["dispatch_bucket"] = incident_data.dispatch_bucket
            if getattr(incident_data, "sla_hours", None):
                metadata["sla_hours"] = incident_data.sla_hours

            metadata["classification"] = {
                "pest_type": incident_data.pest_type,
                "confidence": getattr(incident_data, "confidence", None),
                "evidence": getattr(incident_data, "evidence", None),
                "detected_terms": getattr(incident_data, "detected_terms", []),
            }

        return IncidentDraft(
            conversation_id=conversation_id,
            channel=message.channel,
            pest_type=incident_data.pest_type if incident_data else None,
            location=incident_data.location if incident_data else None,
            affected_area=incident_data.affected_area if incident_data else None,
            priority=incident_data.priority if incident_data else "medium",
            summary=incident_data.summary if incident_data else None,
            confidence=getattr(incident_data, "confidence", None) if incident_data else None,
            severity=getattr(incident_data, "severity", None) if incident_data else None,
            operational_priority=self._operational_priority_from_incident(incident_data) if incident_data else None,
            response_hours=getattr(incident_data, "response_hours", None) if incident_data else None,
            assessment_reason=getattr(incident_data, "assessment_reason", None) if incident_data else None,
            visit_type=getattr(incident_data, "visit_type", None) if incident_data else None,
            technician_level=getattr(incident_data, "technician_level", None) if incident_data else None,
            dispatch_bucket=getattr(incident_data, "dispatch_bucket", None) if incident_data else None,
            sla_hours=getattr(incident_data, "sla_hours", None) if incident_data else None,
            metadata=metadata,
        )

    def _operational_priority_from_incident(self, incident_data) -> str | None:
        priority = getattr(incident_data, "priority", None)
        if not isinstance(priority, str):
            return None
        return {
            "urgent": "URGENT",
            "high": "HIGH",
            "medium": "NORMAL",
            "low": "LOW",
        }.get(priority, priority if priority.isupper() else None)

    async def _get_hermes_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        customer_context: Any = None,
        intent: Any = None,
        conversation_state: dict | None = None,
        injected_pest: str | None = None,
        assessment: Any = None,
    ) -> AgentResponse:
        if self._is_pilot_candidate(message):
            return await self._get_pilot_or_fallback_response(
                message,
                conversation_id,
                trace_id,
                customer_context=customer_context,
                intent=intent,
                conversation_state=conversation_state,
                injected_pest=injected_pest,
                assessment=assessment,
            )

        if self.settings.hermes_pilot_mode:
            logger.info(
                "hermes_pilot_skipped trace_id=%s conversation_id=%s reason=channel",
                trace_id,
                conversation_id,
            )
        try:
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            if conversation_state:
                business_context["conversation_state"] = conversation_state
            if injected_pest:
                business_context["injected_pest"] = injected_pest
            if customer_context:
                business_context["customer_context"] = customer_context.model_dump()
            if intent:
                business_context["intent"] = intent.value
            if assessment:
                business_context["assessment"] = assessment.model_dump()

            raw_response = await self.hermes_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            if isinstance(raw_response, AgentResponse):
                return raw_response
            return AgentResponse.model_validate(raw_response)
        except Exception as exc:
            logger.exception("Error en _get_hermes_response: %s", exc)
            return self._build_safe_agent_error_response()

    async def _get_pilot_or_fallback_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        customer_context: Any = None,
        intent: Any = None,
        conversation_state: dict | None = None,
        injected_pest: str | None = None,
        assessment: Any = None,
    ) -> AgentResponse:
        gate_result = self.pilot_gate.evaluate(message)
        if not gate_result.eligible:
            if gate_result.route == "human_review":
                logger.info(
                    "hermes_pilot_blocked trace_id=%s conversation_id=%s route=%s "
                    "policy_rule=%s",
                    trace_id,
                    conversation_id,
                    gate_result.route,
                    gate_result.policy_rule,
                )
                return self._build_pilot_human_review_response(gate_result)

            response = await self._get_primary_hermes_response(
                message,
                conversation_id,
                trace_id,
                conversation_state=conversation_state,
                injected_pest=injected_pest,
                assessment=assessment,
            )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=False,
                    pilot_blocked=True,
                ),
            )
            return response

        if not self._should_sample_pilot():
            response = await self._get_primary_hermes_response(
                message,
                conversation_id,
                trace_id,
                customer_context=customer_context,
                intent=intent,
                conversation_state=conversation_state,
                injected_pest=injected_pest,
                assessment=assessment,
            )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=False,
                    pilot_blocked=True,
                    extra={"pilot_blocked_reason": "sample_rate"},
                ),
            )
            return response

        try:
            pilot_service = self.pilot_hermes_service or self._build_pilot_hermes_service()
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            business_context["pilot_mode"] = True
            if conversation_state:
                business_context["conversation_state"] = conversation_state
            if injected_pest:
                business_context["injected_pest"] = injected_pest
            if customer_context:
                business_context["customer_context"] = customer_context.model_dump()
            if intent:
                business_context["intent"] = intent.value
            if assessment:
                business_context["assessment"] = assessment.model_dump()

            raw_response = await pilot_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            response = (
                raw_response
                if isinstance(raw_response, AgentResponse)
                else AgentResponse.model_validate(raw_response)
            )
            if bool(response.metadata.get("fallback_used", False)):
                return await self._pilot_fallback_to_primary(
                    message,
                    conversation_id,
                    trace_id,
                    gate_result,
                    response.metadata.get("fallback_reason") or "agent_fallback",
                    assessment=assessment,
                )
            if len(response.reply or "") > self.settings.hermes_pilot_max_response_length:
                return await self._pilot_fallback_to_primary(
                    message,
                    conversation_id,
                    trace_id,
                    gate_result,
                    "max_response_length",
                    assessment=assessment,
                )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=True,
                    pilot_blocked=False,
                    extra={
                        "effective_hermes_mode": "pilot",
                        "pilot_agent_hermes_mode": getattr(
                            pilot_service,
                            "hermes_mode",
                            "real",
                        ),
                    },
                ),
            )
            logger.info(
                "hermes_pilot_used trace_id=%s conversation_id=%s action_type=%s",
                trace_id,
                conversation_id,
                response.action.type,
            )
            return response
        except Exception as exc:
            return await self._pilot_fallback_to_primary(
                message,
                conversation_id,
                trace_id,
                gate_result,
                f"UnexpectedError:{exc.__class__.__name__}",
                assessment=assessment,
            )

    async def _get_primary_hermes_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        customer_context: Any = None,
        intent: Any = None,
        conversation_state: dict | None = None,
        injected_pest: str | None = None,
        assessment: Any = None,
    ) -> AgentResponse:
        try:
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            if conversation_state:
                business_context["conversation_state"] = conversation_state
            if injected_pest:
                business_context["injected_pest"] = injected_pest
            if customer_context:
                business_context["customer_context"] = customer_context.model_dump()
            if intent:
                business_context["intent"] = intent.value
            if assessment:
                business_context["assessment"] = assessment.model_dump()

            raw_response = await self.hermes_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            if isinstance(raw_response, AgentResponse):
                return raw_response
            return AgentResponse.model_validate(raw_response)
        except Exception:
            return self._build_safe_agent_error_response()

    async def _pilot_fallback_to_primary(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        gate_result: PilotGateResult,
        fallback_reason: str,
        assessment: Any = None,
    ) -> AgentResponse:
        logger.warning(
            "hermes_pilot_fallback trace_id=%s conversation_id=%s reason=%s",
            trace_id,
            conversation_id,
            fallback_reason,
        )
        response = await self._get_primary_hermes_response(
            message,
            conversation_id,
            trace_id,
            customer_context=None, # In a full refactor, we would pass these down, but fallback is ok
            intent=None,
            assessment=assessment,
        )
        self._merge_metadata(
            response,
            self._pilot_metadata(
                gate_result=gate_result,
                pilot_used=False,
                pilot_blocked=False,
                extra={
                    "fallback_used": True,
                    "fallback_reason": str(fallback_reason),
                    "pilot_agent_failed": True,
                },
            ),
        )
        return response

    def _build_pilot_human_review_response(
        self,
        gate_result: PilotGateResult,
    ) -> AgentResponse:
        return AgentResponse(
            reply=(
                "Gracias por avisarnos. Por seguridad, voy a pasar este caso al "
                "equipo para que lo revise antes de darte indicaciones."
            ),
            action={
                "type": "escalate_to_human",
                "missing_fields": [],
            },
            incident={
                "should_create": True,
                "pest_type": None,
                "location": None,
                "affected_area": None,
                "priority": "urgent",
                "summary": (
                    "Caso bloqueado por Pilot Gate. Requiere revisión humana antes "
                    "de delegar en Hermes Agent."
                ),
            },
            metadata=self._pilot_metadata(
                gate_result=gate_result,
                pilot_used=False,
                pilot_blocked=True,
                extra={"sensitive_case": True},
            ),
        )

    def _pilot_metadata(
        self,
        gate_result: PilotGateResult,
        pilot_used: bool,
        pilot_blocked: bool,
        extra: dict | None = None,
    ) -> dict:
        metadata = {
            "pilot_mode": True,
            "pilot_used": pilot_used,
            "pilot_blocked": pilot_blocked,
            "pilot_gate_eligible": gate_result.eligible,
            "pilot_route": gate_result.route,
            "pilot_blocked_reason": gate_result.reason if pilot_blocked else None,
            "pilot_risk_flags": gate_result.risk_flags,
            "pilot_policy_rule": gate_result.policy_rule,
        }
        if extra:
            metadata.update(extra)
        return metadata

    def _merge_metadata(self, response: AgentResponse, metadata: dict) -> None:
        response.metadata.update(
            {key: value for key, value in metadata.items() if value is not None}
        )

    def _is_pilot_candidate(self, message: IncomingMessage) -> bool:
        if not self.settings.hermes_pilot_mode:
            return False
        allowed_channels = {
            channel.strip()
            for channel in self.settings.hermes_pilot_allowed_channels.split(",")
            if channel.strip()
        }
        if allowed_channels and message.channel not in allowed_channels:
            return False
        return True

    def _should_sample_pilot(self) -> bool:
        sample_rate = max(0.0, min(1.0, self.settings.hermes_pilot_sample_rate))
        return self.random_func() < sample_rate

    def _build_pilot_hermes_service(self) -> HermesService:
        return HermesService.for_pilot(self.settings)

    def _build_safe_agent_error_response(self) -> AgentResponse:
        return AgentResponse(
            reply=(
                "Ahora mismo no he podido procesar correctamente tu solicitud. "
                "He dejado constancia para que el equipo lo revise."
            ),
            action={
                "type": "escalate_to_human",
                "missing_fields": [],
            },
            incident={
                "should_create": True,
                "pest_type": None,
                "location": None,
                "affected_area": None,
                "priority": "medium",
                "summary": "Error procesando respuesta del agente. Requiere revisión humana.",
            },
            metadata={
                "fallback_used": True,
                "fallback_reason": "conversation_service_invalid_agent_response",
            },
        )

    async def _upsert_conversation(
        self,
        message: IncomingMessage,
        conversation_id: str,
    ) -> None:
        existing_conversation = await self.firestore_service.get_document(
            "conversations",
            conversation_id,
        )
        conversation_data = {
            "id": conversation_id,
            "channel": message.channel,
            "external_user_id": message.external_user_id,
            "external_chat_id": message.external_chat_id,
            "status": "active",
        }

        if existing_conversation is None:
            await self.firestore_service.create_document(
                "conversations",
                conversation_data,
                document_id=conversation_id,
            )
            return

        await self.firestore_service.update_document(
            "conversations",
            conversation_id,
            conversation_data,
        )

    async def _upsert_conversation_with_state(
        self,
        message: IncomingMessage,
        conversation_id: str,
        conv_state: dict,
    ) -> None:
        existing_conversation = await self.firestore_service.get_document(
            "conversations",
            conversation_id,
        )
        conversation_data = {
            "id": conversation_id,
            "channel": message.channel,
            "external_user_id": message.external_user_id,
            "external_chat_id": message.external_chat_id,
            "status": "active",
            "conversation_state": conv_state,
        }

        if existing_conversation is None:
            await self.firestore_service.create_document(
                "conversations",
                conversation_data,
                document_id=conversation_id,
            )
            return

        await self.firestore_service.update_document(
            "conversations",
            conversation_id,
            conversation_data,
        )

    async def _store_inbound_message(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
    ) -> dict:
        return await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "direction": "inbound",
                "channel": message.channel,
                "text": message.text,
                "attachments": message.attachments,
                "metadata": message.metadata,
            },
        )

    async def _store_outbound_message(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        response: AgentResponse,
    ) -> None:
        await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "direction": "outbound",
                "channel": message.channel,
                "text": response.reply,
                "attachments": [],
                "metadata": {},
            },
        )

    async def _record_decision(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        message_id: str | None,
        incident_id: str | None,
        response: AgentResponse,
    ):
        incident_should_create = (
            response.incident.should_create if response.incident is not None else False
        )
        fallback_used = bool(response.metadata.get("fallback_used", False))
        fallback_reason = response.metadata.get("fallback_reason")
        decision_record = DecisionRecordCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            message_id=message_id,
            incident_id=incident_id,
            channel=message.channel,
            hermes_mode=response.metadata.get(
                "effective_hermes_mode",
                getattr(self.hermes_service, "hermes_mode", "unknown"),
            ),
            action_type=response.action.type,
            incident_should_create=incident_should_create,
            pest_type=response.incident.pest_type if response.incident else None,
            priority=response.incident.priority if response.incident else None,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            pilot_mode_enabled=bool(response.metadata.get("pilot_mode", False)),
            pilot_used=bool(response.metadata.get("pilot_used", False)),
            pilot_blocked=bool(response.metadata.get("pilot_blocked", False)),
            pilot_blocked_reason=response.metadata.get("pilot_blocked_reason"),
            pilot_route=response.metadata.get("pilot_route"),
            pilot_risk_flags=response.metadata.get("pilot_risk_flags", []),
            pilot_policy_rule=response.metadata.get("pilot_policy_rule"),
            metadata={
                "message_type": message.message_type,
                "missing_fields": response.action.missing_fields,
                "pilot_mode": bool(response.metadata.get("pilot_mode", False)),
                "pilot_used": bool(response.metadata.get("pilot_used", False)),
                "pilot_blocked": bool(response.metadata.get("pilot_blocked", False)),
                "pilot_gate_eligible": response.metadata.get("pilot_gate_eligible"),
                "pilot_route": response.metadata.get("pilot_route"),
                "pilot_blocked_reason": response.metadata.get("pilot_blocked_reason"),
                "pilot_risk_flags": response.metadata.get("pilot_risk_flags", []),
                "pilot_policy_rule": response.metadata.get("pilot_policy_rule"),
                "pilot_agent_failed": bool(
                    response.metadata.get("pilot_agent_failed", False)
                ),
            },
        )
        created_decision_record = (
            await self.decision_audit_service.create_decision_record(decision_record)
        )
        logger.info(
            "decision_record_created trace_id=%s conversation_id=%s action_type=%s "
            "fallback_used=%s",
            trace_id,
            conversation_id,
            response.action.type,
            fallback_used,
        )
        return created_decision_record

    async def _create_human_review_item_if_needed(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        incident_id: str | None,
        decision_record_id: str | None,
        response: AgentResponse,
    ) -> None:
        reasons = self._human_review_reasons(response)
        if not reasons:
            return

        priority = response.incident.priority if response.incident else "medium"
        summary = (
            response.incident.summary
            if response.incident and response.incident.summary
            else response.reply
        )
        review_item = HumanReviewItemCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            incident_id=incident_id,
            decision_record_id=decision_record_id,
            channel=message.channel,
            reason=reasons[0],
            priority=priority,
            summary=summary,
            metadata={
                "review_reasons": reasons,
                "action_type": response.action.type,
                "fallback_reason": response.metadata.get("fallback_reason"),
                "missing_fields": response.action.missing_fields,
            },
        )
        created_review_item = await self.human_review_service.create_review_item(
            review_item
        )
        logger.info(
            "human_review_item_created trace_id=%s conversation_id=%s review_item_id=%s "
            "reason=%s priority=%s",
            trace_id,
            conversation_id,
            created_review_item.id,
            reasons[0],
            priority,
        )

    def _human_review_reasons(self, response: AgentResponse) -> list[str]:
        reasons = []
        fallback_used = bool(response.metadata.get("fallback_used", False))
        priority = response.incident.priority if response.incident else None

        if fallback_used:
            reasons.append("fallback_used")
        if response.action.type == "escalate_to_human":
            reasons.append("agent_escalation")
        if priority == "urgent":
            reasons.append("urgent_priority")
        if response.metadata.get("sensitive_case") is True:
            reasons.append("sensitive_case")

        return reasons

    async def _run_shadow_if_enabled(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        primary_response: AgentResponse,
    ) -> None:
        if not HermesService.shadow_enabled(self.settings):
            return
        if (
            self.shadow_hermes_service is None
            and not HermesService.shadow_runtime_configured(self.settings)
        ):
            logger.warning(
                "hermes_shadow_skipped trace_id=%s conversation_id=%s "
                "reason=missing_shadow_api_url",
                trace_id,
                conversation_id,
            )
            return
        if not self._should_sample_shadow():
            logger.info(
                "hermes_shadow_skipped trace_id=%s conversation_id=%s reason=sample_rate",
                trace_id,
                conversation_id,
            )
            return

        shadow_service = self.shadow_hermes_service or self._build_shadow_hermes_service()
        business_context = default_business_context(conversation_id)
        business_context["trace_id"] = trace_id
        business_context["shadow_mode"] = True

        shadow_response: AgentResponse | None = None
        shadow_error: str | None = None
        shadow_fallback_reason: str | None = None

        try:
            raw_shadow_response = await shadow_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            shadow_response = (
                raw_shadow_response
                if isinstance(raw_shadow_response, AgentResponse)
                else AgentResponse.model_validate(raw_shadow_response)
            )
            if bool(shadow_response.metadata.get("fallback_used", False)):
                shadow_fallback_reason = str(
                    shadow_response.metadata.get("fallback_reason")
                    or "HermesClientError:unknown"
                )
                shadow_error = shadow_fallback_reason
        except Exception as exc:
            shadow_error = f"UnexpectedError:{exc.__class__.__name__}"
            logger.warning(
                "hermes_shadow_error trace_id=%s conversation_id=%s error=%s",
                trace_id,
                conversation_id,
                shadow_error,
            )

        await self.shadow_decision_service.create_shadow_record(
            self._build_shadow_record(
                message=message,
                conversation_id=conversation_id,
                trace_id=trace_id,
                primary_response=primary_response,
                shadow_response=shadow_response,
                shadow_error=shadow_error,
                shadow_fallback_reason=shadow_fallback_reason,
                shadow_hermes_mode=getattr(shadow_service, "hermes_mode", "real"),
            )
        )
        logger.info(
            "hermes_shadow_record_created trace_id=%s conversation_id=%s "
            "primary_action=%s shadow_action=%s shadow_error=%s",
            trace_id,
            conversation_id,
            primary_response.action.type,
            shadow_response.action.type if shadow_response else None,
            shadow_error,
        )

    def _should_sample_shadow(self) -> bool:
        sample_rate = max(0.0, min(1.0, self.settings.hermes_shadow_sample_rate))
        return self.random_func() < sample_rate

    def _build_shadow_hermes_service(self) -> HermesService:
        return HermesService.for_shadow(self.settings)

    def _build_shadow_record(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        primary_response: AgentResponse,
        shadow_response: AgentResponse | None,
        shadow_error: str | None,
        shadow_fallback_reason: str | None,
        shadow_hermes_mode: str,
    ) -> ShadowDecisionRecordCreate:
        differences = self._compare_shadow_response(primary_response, shadow_response)
        return ShadowDecisionRecordCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            channel=message.channel,
            primary_hermes_mode=getattr(self.hermes_service, "hermes_mode", "unknown"),
            shadow_hermes_mode=shadow_hermes_mode,
            primary_action_type=primary_response.action.type,
            shadow_action_type=shadow_response.action.type if shadow_response else None,
            primary_priority=(
                primary_response.incident.priority if primary_response.incident else None
            ),
            shadow_priority=(
                shadow_response.incident.priority
                if shadow_response and shadow_response.incident
                else None
            ),
            primary_pest_type=(
                primary_response.incident.pest_type if primary_response.incident else None
            ),
            shadow_pest_type=(
                shadow_response.incident.pest_type
                if shadow_response and shadow_response.incident
                else None
            ),
            primary_should_create=(
                primary_response.incident.should_create
                if primary_response.incident
                else False
            ),
            shadow_should_create=(
                shadow_response.incident.should_create
                if shadow_response and shadow_response.incident
                else None
            ),
            agreement_summary=self._agreement_summary(differences, shadow_error),
            differences=differences,
            shadow_fallback_used=(
                bool(shadow_response.metadata.get("fallback_used", False))
                if shadow_response
                else False
            ),
            shadow_error=shadow_error,
            metadata={
                "message_type": message.message_type,
                "primary_missing_fields": primary_response.action.missing_fields,
                "shadow_missing_fields": (
                    shadow_response.action.missing_fields if shadow_response else []
                ),
                "shadow_fallback_reason": shadow_fallback_reason,
            },
        )

    def _compare_shadow_response(
        self,
        primary_response: AgentResponse,
        shadow_response: AgentResponse | None,
    ) -> dict:
        if shadow_response is None:
            return {"shadow_response": {"primary": "present", "shadow": None}}

        comparisons = {
            "action_type": (
                primary_response.action.type,
                shadow_response.action.type,
            ),
            "priority": (
                primary_response.incident.priority if primary_response.incident else None,
                shadow_response.incident.priority if shadow_response.incident else None,
            ),
            "pest_type": (
                primary_response.incident.pest_type if primary_response.incident else None,
                shadow_response.incident.pest_type if shadow_response.incident else None,
            ),
            "should_create": (
                primary_response.incident.should_create
                if primary_response.incident
                else False,
                shadow_response.incident.should_create
                if shadow_response.incident
                else False,
            ),
        }
        return {
            field: {"primary": primary, "shadow": shadow}
            for field, (primary, shadow) in comparisons.items()
            if primary != shadow
        }

    def _agreement_summary(self, differences: dict, shadow_error: str | None) -> str:
        if shadow_error:
            return "shadow_error"
        if not differences:
            return "full_agreement"
        return "differences_detected"
