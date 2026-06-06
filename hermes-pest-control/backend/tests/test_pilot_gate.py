from app.schemas.incoming_message import IncomingMessage
from app.services.pilot_gate import HermesPilotGate


def _message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="pilot-user",
        external_chat_id="pilot-chat",
        message_type="text",
        text=text,
    )


def test_pilot_gate_allows_simple_cockroach_case() -> None:
    result = HermesPilotGate().evaluate(
        _message("Tengo cucarachas en la cocina en Torremolinos desde hace una semana")
    )

    assert result.eligible is True
    assert result.route == "agent"
    assert result.policy_rule == "pilot.simple_intake"


def test_pilot_gate_allows_simple_ant_case() -> None:
    result = HermesPilotGate().evaluate(
        _message("Hay hormigas en el jardín en Málaga desde ayer")
    )

    assert result.eligible is True
    assert result.route == "agent"


def test_pilot_gate_blocks_chemical_request_to_human_review() -> None:
    result = HermesPilotGate().evaluate(
        _message("Tengo cucarachas, dime qué producto químico puedo mezclar")
    )

    assert result.eligible is False
    assert result.route == "human_review"
    assert "chemical_request" in result.risk_flags


def test_pilot_gate_blocks_pet_exposure_to_human_review() -> None:
    result = HermesPilotGate().evaluate(
        _message("Mi perro ha tocado producto y hay cucarachas en casa")
    )

    assert result.eligible is False
    assert result.route == "human_review"
    assert "exposure_or_pet" in result.risk_flags


def test_pilot_gate_blocks_vulnerable_person_to_human_review() -> None:
    result = HermesPilotGate().evaluate(
        _message("Hay chinches en dormitorio en Málaga y tenemos un bebé en casa")
    )

    assert result.eligible is False
    assert result.route == "human_review"
    assert "vulnerable_person" in result.risk_flags


def test_pilot_gate_allows_food_business_case() -> None:
    result = HermesPilotGate().evaluate(
        _message("Tenemos ratas en la cocina del restaurante en Málaga")
    )

    assert result.eligible is True
    assert result.route == "agent"



def test_pilot_gate_routes_exact_price_to_mock() -> None:
    result = HermesPilotGate().evaluate(
        _message("Quiero precio exacto para cucarachas en cocina en Torremolinos")
    )

    assert result.eligible is False
    assert result.route == "mock"
    assert "price_request" in result.risk_flags


def test_pilot_gate_blocks_angry_rodent_case_to_human_review() -> None:
    result = HermesPilotGate().evaluate(
        _message("Estoy muy enfadado, hay roedores y voy a denunciar")
    )

    assert result.eligible is False
    assert result.route == "human_review"
    assert "rodent_conflict" in result.risk_flags


def test_pilot_gate_routes_ambiguous_message_to_mock() -> None:
    result = HermesPilotGate().evaluate(_message("Hay bichos"))

    assert result.eligible is False
    assert result.route == "mock"
    assert "ambiguous_message" in result.risk_flags
