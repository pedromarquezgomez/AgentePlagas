import pytest

from app.adapters.whatsapp_adapter import WhatsAppAdapter, WhatsAppAdapterError
from app.config.settings import Settings
from app.schemas.outgoing_message import OutgoingMessage


def whatsapp_text_payload() -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "34999000111",
                                "phone_number_id": "phone-number-id",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Pedro"},
                                    "wa_id": "34600000000",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "34600000000",
                                    "id": "wamid.123",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {
                                        "body": "Tengo cucarachas en la cocina en Torremolinos",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def test_whatsapp_adapter_parse_incoming_text_message() -> None:
    adapter = WhatsAppAdapter()

    message = adapter.parse_incoming(whatsapp_text_payload())

    assert message.channel == "whatsapp"
    assert message.external_user_id == "34600000000"
    assert message.external_chat_id == "34600000000"
    assert message.message_type == "text"
    assert message.text == "Tengo cucarachas en la cocina en Torremolinos"
    assert message.attachments == []
    assert message.metadata["whatsapp_message_id"] == "wamid.123"
    assert message.metadata["contact_name"] == "Pedro"
    assert message.metadata["phone_number_id"] == "phone-number-id"


def test_whatsapp_adapter_rejects_invalid_payload() -> None:
    adapter = WhatsAppAdapter()

    with pytest.raises(WhatsAppAdapterError):
        adapter.parse_incoming({"object": "whatsapp_business_account"})


def test_whatsapp_adapter_parse_incoming_attachment() -> None:
    payload = whatsapp_text_payload()
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message.clear()
    message.update(
        {
            "from": "34600000000",
            "id": "wamid.image",
            "timestamp": "1710000001",
            "type": "image",
            "image": {
                "id": "media-id",
                "mime_type": "image/jpeg",
                "sha256": "hash",
                "caption": "Foto de la cocina",
            },
        }
    )

    parsed = WhatsAppAdapter().parse_incoming(payload)

    assert parsed.message_type == "text"
    assert parsed.text == "Foto de la cocina"
    assert parsed.attachments == [
        {
            "type": "image",
            "id": "media-id",
            "mime_type": "image/jpeg",
            "sha256": "hash",
            "filename": None,
            "caption": "Foto de la cocina",
        }
    ]


@pytest.mark.asyncio
async def test_whatsapp_adapter_send_message_mock_provider() -> None:
    adapter = WhatsAppAdapter(
        Settings(whatsapp_enabled=True, whatsapp_provider="mock")
    )

    response = await adapter.send_message(
        OutgoingMessage(
            channel="whatsapp",
            external_chat_id="34600000000",
            text="Respuesta de prueba",
        )
    )

    assert response["mock"] is True
    assert response["to"] == "34600000000"
