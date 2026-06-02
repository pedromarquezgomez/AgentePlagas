from datetime import datetime, timezone

from app.schemas.tool_harness import ToolExecutionRecord, ToolExecutionRecordUpdate
from app.services.firestore_factory import get_firestore_service
from app.services.gmail_tool_executor import (
    GmailToolDisabledError,
    GmailToolExecutionError,
    GmailToolExecutor,
    GmailToolPayloadError,
)


class ToolExecutionRecordNotFoundError(LookupError):
    pass


class ToolExecutionNotApprovedError(RuntimeError):
    pass


class ToolExecutionAlreadyExecutedError(RuntimeError):
    pass


class ToolExecutionUnsupportedError(RuntimeError):
    pass


class ToolExecutionService:
    collection_name = "tool_execution_records"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_execution_record(
        self,
        execution_record: ToolExecutionRecord,
    ) -> ToolExecutionRecord:
        stored_record = await self.firestore_service.create_document(
            self.collection_name,
            execution_record.model_dump(exclude={"created_at", "updated_at", "reviewed_at"}),
            document_id=execution_record.id,
        )
        return ToolExecutionRecord.model_validate(stored_record)

    async def list_execution_records(
        self,
        review_status: str | None = None,
        tool_name: str | None = None,
        provider: str | None = None,
        decision: str | None = None,
        risk_level: int | None = None,
        requires_approval: bool | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if review_status:
            filters["review_status"] = review_status
        if tool_name:
            filters["tool_name"] = tool_name
        if provider:
            filters["provider"] = provider
        if decision:
            filters["decision"] = decision
        if risk_level is not None:
            filters["risk_level"] = risk_level
        if requires_approval is not None:
            filters["requires_approval"] = requires_approval

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )

    async def get_execution_record(self, execution_id: str) -> dict:
        record = await self.firestore_service.get_document(
            self.collection_name,
            execution_id,
        )
        if record is None:
            raise ToolExecutionRecordNotFoundError(
                f"Tool execution record not found: {execution_id}"
            )
        return record

    async def update_execution_record(
        self,
        execution_id: str,
        update: ToolExecutionRecordUpdate,
    ) -> dict:
        current_record = await self.firestore_service.get_document(
            self.collection_name,
            execution_id,
        )
        if current_record is None:
            raise ToolExecutionRecordNotFoundError(
                f"Tool execution record not found: {execution_id}"
            )

        updates = update.model_dump(exclude_unset=True)
        if update.review_status in {
            "approved",
            "rejected",
            "needs_more_info",
            "dismissed",
        }:
            updates["reviewed_at"] = datetime.now(timezone.utc)

        await self.firestore_service.update_document(
            self.collection_name,
            execution_id,
            updates,
        )

        updated_record = await self.firestore_service.get_document(
            self.collection_name,
            execution_id,
        )
        if updated_record is None:
            raise ToolExecutionRecordNotFoundError(
                f"Tool execution record not found after update: {execution_id}"
            )
        return updated_record

    async def execute_execution_record(
        self,
        execution_id: str,
        gmail_executor: GmailToolExecutor | None = None,
    ) -> dict:
        current_record = await self.firestore_service.get_document(
            self.collection_name,
            execution_id,
        )
        if current_record is None:
            raise ToolExecutionRecordNotFoundError(
                f"Tool execution record not found: {execution_id}"
            )

        if current_record.get("review_status") != "approved":
            raise ToolExecutionNotApprovedError(
                "Tool execution requires review_status=approved."
            )
        if current_record.get("executed") is True:
            raise ToolExecutionAlreadyExecutedError(
                "Tool execution record has already been executed."
            )
        if not self._is_gmail_create_draft(current_record):
            raise ToolExecutionUnsupportedError(
                "Only gmail.create_draft can be executed in this sprint."
            )

        payload = self._execution_payload(current_record)
        executor = gmail_executor or GmailToolExecutor()

        try:
            result = await executor.create_draft(payload)
        except GmailToolDisabledError:
            raise
        except GmailToolPayloadError:
            raise
        except GmailToolExecutionError:
            raise

        await self.firestore_service.update_document(
            self.collection_name,
            execution_id,
            {
                "executed": True,
                "external_effect": True,
                "execution_status": "executed",
                "execution_result": result,
                "execution_error": None,
                "executed_at": datetime.now(timezone.utc),
            },
        )

        updated_record = await self.firestore_service.get_document(
            self.collection_name,
            execution_id,
        )
        if updated_record is None:
            raise ToolExecutionRecordNotFoundError(
                f"Tool execution record not found after execution: {execution_id}"
            )
        return updated_record

    def _is_gmail_create_draft(self, record: dict) -> bool:
        return (
            record.get("provider") == "gmail"
            and record.get("tool_name") == "gmail.create_draft"
            and record.get("action") == "create_draft"
        )

    def _execution_payload(self, record: dict) -> dict:
        if isinstance(record.get("approved_payload"), dict) and record["approved_payload"]:
            return dict(record["approved_payload"])

        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        payload = metadata.get("payload")
        return dict(payload) if isinstance(payload, dict) else {}
