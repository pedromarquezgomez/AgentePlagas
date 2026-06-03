from app.skills.contracts import ProductSkill


DEFAULT_PRODUCT_SKILLS = [
    ProductSkill(
        name="classify_pest",
        description="Identify the pest type from the customer message.",
        allowed_outputs=["pest_type", "confidence", "missing_fields"],
        forbidden_effects=["database_write", "channel_send", "tool_execution"],
        risk_level="low",
        instructions=(
            "Classify the pest type into cockroach, rodent, ant, or unknown. "
            "Normalize common terms: cucarachas -> cockroach, roedores/ratas/ratones -> rodent, "
            "hormigas -> ant. If uncertain, leave as unknown."
        ),
    ),
    ProductSkill(
        name="request_missing_info",
        description="Ask only for the operational fields still missing.",
        allowed_outputs=["reply", "action.collect_missing_data", "missing_fields"],
        forbidden_effects=["database_write", "channel_send", "tool_execution"],
        risk_level="low",
        instructions=(
            "Required intake fields are pest_type, location, and customer_name. "
            "Preserve known fields and ask only for missing or uncertain data."
        ),
    ),
    ProductSkill(
        name="create_incident",
        description="Propose an incident when intake is complete and safe.",
        allowed_outputs=["action.create_incident", "incident"],
        forbidden_effects=["database_write", "direct_firestore_write"],
        risk_level="medium",
        instructions=(
            "Return an AgentResponse proposal only. The backend IncidentService "
            "is the only component allowed to persist the incident."
        ),
    ),
    ProductSkill(
        name="escalate_to_human",
        description="Escalate sensitive, unsafe, legal, pricing, or unclear cases.",
        allowed_outputs=["action.escalate_to_human", "incident", "reply"],
        forbidden_effects=["medical_advice", "chemical_instructions", "channel_send"],
        risk_level="high",
        instructions=(
            "Escalate cases involving chemical exposure, vulnerable people, pets, "
            "food businesses, threats, exact prices, guarantees, or dangerous "
            "instructions."
        ),
    ),
    ProductSkill(
        name="suggest_visit",
        description="Suggest that a visit may be needed without scheduling it.",
        allowed_outputs=["reply", "tool_request.propose_calendar_event"],
        forbidden_effects=["calendar_write", "visit_write", "technician_assignment"],
        risk_level="medium",
        instructions=(
            "The agent may propose a visit or draft a calendar request. VisitService "
            "and human operators control actual scheduling."
        ),
    ),
    ProductSkill(
        name="summarize_case",
        description="Summarize the case for operators or draft documents.",
        allowed_outputs=["summary", "reply", "document_draft"],
        forbidden_effects=["document_persist", "database_write", "channel_send"],
        risk_level="low",
        instructions=(
            "Create concise operational summaries. Do not create legal certificates "
            "or persist documents directly."
        ),
    ),
]
