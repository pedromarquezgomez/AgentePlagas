import pytest

from app.config.settings import Settings
from app.services.gmail_tool_executor import (
    GmailToolDisabledError,
    GmailToolExecutor,
    GmailToolPayloadError,
)


class _MockExecute:
    def execute(self) -> dict:
        return {"id": "draft-1", "message": {"id": "message-1"}}


class _MockDrafts:
    def __init__(self) -> None:
        self.created_body = None

    def create(self, userId: str, body: dict) -> _MockExecute:
        assert userId == "me"
        assert body["message"]["raw"]
        self.created_body = body
        return _MockExecute()


class _MockUsers:
    def __init__(self, drafts: _MockDrafts) -> None:
        self._drafts = drafts

    def drafts(self) -> _MockDrafts:
        return self._drafts

    def getProfile(self, userId: str) -> _MockExecute:
        assert userId == "me"
        return _MockProfileExecute()


class _MockProfileExecute:
    def execute(self) -> dict:
        return {
            "emailAddress": "hermes@example.test",
            "messagesTotal": 10,
            "threadsTotal": 5,
        }


class _MockGmailService:
    def __init__(self) -> None:
        self.drafts_resource = _MockDrafts()

    def users(self) -> _MockUsers:
        return _MockUsers(self.drafts_resource)


@pytest.mark.asyncio
async def test_gmail_executor_rejects_when_disabled() -> None:
    executor = GmailToolExecutor(settings=Settings())

    with pytest.raises(GmailToolDisabledError):
        await executor.create_draft(
            {
                "recipient": "cliente@example.test",
                "subject": "Resumen",
                "body": "Borrador.",
            }
        )


def test_gmail_executor_validates_payload() -> None:
    executor = GmailToolExecutor(
        settings=Settings(
            gmail_tools_enabled=True,
            gmail_draft_execution_enabled=True,
        )
    )

    with pytest.raises(GmailToolPayloadError):
        executor.validate_payload(
            {
                "recipient": "",
                "subject": "Resumen",
                "body": "Borrador.",
            }
        )


@pytest.mark.asyncio
async def test_gmail_executor_creates_draft_with_mock_service() -> None:
    gmail_service = _MockGmailService()
    executor = GmailToolExecutor(
        settings=Settings(
            gmail_tools_enabled=True,
            gmail_draft_execution_enabled=True,
        ),
        gmail_service=gmail_service,
    )

    result = await executor.create_draft(
        {
            "to": "cliente@example.test",
            "subject": "Resumen",
            "body": "Borrador revisado.",
        }
    )

    assert result == {
        "provider": "gmail",
        "draft_id": "draft-1",
        "message_id": "message-1",
    }
    assert "Borrador revisado" not in str(result)


@pytest.mark.asyncio
async def test_gmail_executor_checks_connection_with_mock_service() -> None:
    executor = GmailToolExecutor(
        settings=Settings(),
        gmail_service=_MockGmailService(),
    )

    result = await executor.check_connection()

    assert result == {
        "provider": "gmail",
        "email_configured": True,
        "messages_total": 10,
        "threads_total": 5,
    }
