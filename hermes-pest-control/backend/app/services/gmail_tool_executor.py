from __future__ import annotations

import base64
import json
import re
from email.message import EmailMessage
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.settings import Settings


class GmailToolExecutionError(RuntimeError):
    pass


class GmailToolDisabledError(GmailToolExecutionError):
    pass


class GmailToolPayloadError(GmailToolExecutionError):
    pass


class GmailDraftPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recipient: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("recipient must be a valid email address.")
        return normalized

    @field_validator("subject", "body")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty.")
        return normalized


class GmailToolExecutor:
    provider = "gmail"

    def __init__(self, settings: Settings | None = None, gmail_service: Any | None = None) -> None:
        self.settings = settings or Settings()
        self.gmail_service = gmail_service

    @property
    def enabled(self) -> bool:
        return (
            self.settings.gmail_tools_enabled
            and self.settings.gmail_draft_execution_enabled
        )

    async def create_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise GmailToolDisabledError("Gmail draft execution is disabled.")

        draft_payload = self.validate_payload(payload)
        service = self.gmail_service or self._build_service()
        raw_message = self._build_raw_message(draft_payload)
        user_id = self.settings.gmail_delegated_user or "me"

        try:
            draft = (
                service.users()
                .drafts()
                .create(userId=user_id, body={"message": {"raw": raw_message}})
                .execute()
            )
        except Exception as exc:
            raise GmailToolExecutionError("Could not create Gmail draft.") from exc

        return {
            "provider": self.provider,
            "draft_id": draft.get("id"),
            "message_id": (draft.get("message") or {}).get("id"),
        }

    async def check_connection(self) -> dict[str, Any]:
        service = self.gmail_service or self._build_service()
        user_id = self.settings.gmail_delegated_user or "me"
        try:
            profile = service.users().getProfile(userId=user_id).execute()
        except Exception as exc:
            raise GmailToolExecutionError("Could not read Gmail profile.") from exc

        return {
            "provider": self.provider,
            "email_configured": bool(profile.get("emailAddress")),
            "messages_total": profile.get("messagesTotal"),
            "threads_total": profile.get("threadsTotal"),
        }

    def validate_payload(self, payload: dict[str, Any]) -> GmailDraftPayload:
        normalized = dict(payload)
        if "recipient" not in normalized and "to" in normalized:
            normalized["recipient"] = normalized["to"]

        try:
            return GmailDraftPayload.model_validate(normalized)
        except Exception as exc:
            raise GmailToolPayloadError("Invalid Gmail draft payload.") from exc

    def _build_service(self) -> Any:
        if not (self.settings.gmail_credentials_json or self.settings.gmail_credentials_path):
            raise GmailToolDisabledError("Gmail credentials are not configured.")

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/gmail.compose"]
            if self.settings.gmail_credentials_json:
                info = json.loads(self.settings.gmail_credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=scopes,
                )
            else:
                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.gmail_credentials_path,
                    scopes=scopes,
                )

            if self.settings.gmail_delegated_user:
                credentials = credentials.with_subject(self.settings.gmail_delegated_user)

            return build("gmail", "v1", credentials=credentials, cache_discovery=False)
        except GmailToolExecutionError:
            raise
        except Exception as exc:
            raise GmailToolExecutionError("Could not initialize Gmail service.") from exc

    def _build_raw_message(self, payload: GmailDraftPayload) -> str:
        message = EmailMessage()
        message["To"] = payload.recipient
        message["Subject"] = payload.subject
        message.set_content(payload.body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return encoded.rstrip("=")
