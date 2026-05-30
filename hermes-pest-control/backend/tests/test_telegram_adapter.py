import pytest

from app.adapters.telegram_adapter import TelegramAdapter, TelegramAdapterError


def test_telegram_adapter_parse_incoming_text_message() -> None:
    adapter = TelegramAdapter()

    message = adapter.parse_incoming(
        {
            "update_id": 1000,
            "message": {
                "message_id": 55,
                "from": {
                    "id": 12345,
                    "is_bot": False,
                    "first_name": "Pedro",
                    "username": "pedro_test",
                },
                "chat": {"id": 67890, "type": "private"},
                "date": 1710000000,
                "text": "Tengo cucarachas",
            },
        }
    )

    assert message.channel == "telegram"
    assert message.external_user_id == "12345"
    assert message.external_chat_id == "67890"
    assert message.message_type == "text"
    assert message.text == "Tengo cucarachas"
    assert message.attachments == []
    assert message.metadata["message_id"] == 55
    assert message.metadata["telegram_date"] == 1710000000
    assert message.metadata["username"] == "pedro_test"
    assert message.metadata["first_name"] == "Pedro"


def test_telegram_adapter_parse_incoming_invalid_payload() -> None:
    adapter = TelegramAdapter()

    with pytest.raises(TelegramAdapterError):
        adapter.parse_incoming({"update_id": 1000})


def test_telegram_adapter_parse_incoming_photo_attachment() -> None:
    adapter = TelegramAdapter()

    message = adapter.parse_incoming(
        {
            "update_id": 1000,
            "message": {
                "message_id": 56,
                "from": {"id": 12345, "first_name": "Pedro"},
                "chat": {"id": 67890, "type": "private"},
                "date": 1710000001,
                "caption": "Foto de la cocina",
                "photo": [
                    {
                        "file_id": "small-file-id",
                        "file_unique_id": "small-unique",
                        "width": 90,
                        "height": 90,
                        "file_size": 1000,
                    },
                    {
                        "file_id": "large-file-id",
                        "file_unique_id": "large-unique",
                        "width": 1280,
                        "height": 720,
                        "file_size": 50000,
                    },
                ],
            },
        }
    )

    assert message.message_type == "text"
    assert message.text == "Foto de la cocina"
    assert len(message.attachments) == 2
    assert message.attachments[1] == {
        "type": "photo",
        "file_id": "large-file-id",
        "file_unique_id": "large-unique",
        "width": 1280,
        "height": 720,
        "file_size": 50000,
    }

