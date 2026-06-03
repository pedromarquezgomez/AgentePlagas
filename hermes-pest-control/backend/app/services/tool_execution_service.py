from datetime import datetime, timezone

from app.audit.contracts import AuditEvent, AuditEventType
from app.audit.service import AuditService, default_audit_service
from app.schemas.tool_harness import ToolExecutionRecord, ToolExecutionRecordUpdate
from app.services.firestore_factory import get_firestore_service
from app.services.gmail_tool_executor import (
    GmailToolDisabledError,
    GmailToolExecutionError,
    GmailToolExecutor,
    GmailToolPayloadError,
)
from app.tools.execution_contracts import (
    ToolExecutionError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
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

    def __init__(
        self,
        firestore_service=None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.firestore_service = firestore_service or get_firestore_service()
        self.audit_service = audit_service or default_audit_service()

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

        execution_request = self._execution_request_from_record(current_record)
        if current_record.get("review_status") != "approved":
            execution_error = self._execution_error(
                execution_request,
                error_code="not_approved",
                error_message="Tool execution requires review_status=approved.",
            )
            self._record_execution_failed(current_record, execution_error)
            raise ToolExecutionNotApprovedError(
                "Tool execution requires review_status=approved."
            )
        if current_record.get("executed") is True:
            execution_error = self._execution_error(
                execution_request,
                error_code="already_executed",
                error_message="Tool execution record has already been executed.",
            )
            self._record_execution_failed(current_record, execution_error)
            raise ToolExecutionAlreadyExecutedError(
                "Tool execution record has already been executed."
            )
        is_gmail = self._is_gmail_create_draft(current_record)
        is_incident = current_record.get("tool_name") == "create_incident_tool"

        if not (is_gmail or is_incident):
            execution_error = self._execution_error(
                execution_request,
                error_code="unsupported_tool",
                error_message="Only gmail.create_draft and create_incident_tool can be executed in this sprint.",
            )
            self._record_execution_failed(current_record, execution_error)
            raise ToolExecutionUnsupportedError(
                "Only gmail.create_draft and create_incident_tool can be executed in this sprint."
            )

        self._record_execution_started(current_record)

        try:
            if is_gmail:
                executor = gmail_executor or GmailToolExecutor()
                executor_result = await executor.create_draft(execution_request.payload)
            else:
                from app.schemas.incident import IncidentDraft
                from app.services.incident_service import IncidentService
                incident_service = IncidentService(self.firestore_service)
                payload = execution_request.payload
                draft = IncidentDraft(
                    conversation_id=execution_request.conversation_id or payload.get("conversation_id"),
                    channel=payload.get("channel") or "telegram",
                    pest_type=payload.get("pest_type"),
                    location=payload.get("location"),
                    affected_area=payload.get("affected_area"),
                    priority=payload.get("priority", "medium"),
                    summary=payload.get("summary"),
                    metadata=payload.get("metadata", {}),
                )
                incident = await incident_service.create_incident(draft)
                executor_result = incident.model_dump()
        except GmailToolDisabledError as exc:
            self._record_execution_failed(
                current_record,
                self._execution_error(
                    execution_request,
                    error_code="gmail_tool_disabled",
                    error_message=str(exc),
                ),
            )
            raise
        except GmailToolPayloadError as exc:
            self._record_execution_failed(
                current_record,
                self._execution_error(
                    execution_request,
                    error_code="gmail_payload_invalid",
                    error_message=str(exc),
                ),
            )
            raise
        except GmailToolExecutionError as exc:
            self._record_execution_failed(
                current_record,
                self._execution_error(
                    execution_request,
                    error_code="gmail_execution_failed",
                    error_message=str(exc),
                ),
            )
            raise
        except Exception as exc:
            self._record_execution_failed(
                current_record,
                self._execution_error(
                    execution_request,
                    error_code="execution_failed",
                    error_message=str(exc),
                ),
            )
            raise

        execution_result = ToolExecutionResult(
            execution_id=execution_request.execution_id,
            tool_name=execution_request.tool_name,
            status=ToolExecutionStatus.EXECUTED,
            message="Tool execution completed.",
            result=executor_result,
        )

        await self.firestore_service.update_document(
            self.collection_name,
            execution_id,
            {
                "executed": True,
                "external_effect": True,
                "execution_status": execution_result.status.value,
                "execution_result": execution_result.result,
                "execution_error": None,
                "executed_at": execution_result.executed_at,
            },
        )
        self._record_execution_completed(current_record, execution_result)

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

    def _execution_request_from_record(self, record: dict) -> ToolExecutionRequest:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        requested_by = (
            record.get("reviewed_by")
            or metadata.get("proposed_by")
            or metadata.get("requested_by")
            or record.get("provider")
            or "unknown"
        )
        return ToolExecutionRequest(
            execution_id=str(record.get("id") or ""),
            tool_name=str(record.get("tool_name") or ""),
            requested_by=str(requested_by),
            provider=str(record.get("provider") or "unknown"),
            payload=self._execution_payload(record),
            created_at=record.get("created_at") or datetime.now(timezone.utc),
            trace_id=record.get("trace_id"),
            conversation_id=record.get("conversation_id"),
            metadata={
                "decision": record.get("decision"),
                "review_status": record.get("review_status"),
                "risk_level": record.get("risk_level"),
                "requires_approval": record.get("requires_approval"),
            },
        )

    def _execution_error(
        self,
        execution_request: ToolExecutionRequest,
        *,
        error_code: str,
        error_message: str,
    ) -> ToolExecutionError:
        return ToolExecutionError(
            execution_id=execution_request.execution_id,
            tool_name=execution_request.tool_name,
            error_code=error_code,
            error_message=error_message,
        )

    def _record_execution_started(self, record: dict) -> None:
        self._record_audit_event(
            record,
            event_type=AuditEventType.TOOL_EXECUTION_STARTED,
            status="started",
            message="Tool execution started.",
        )

    def _record_execution_completed(
        self,
        record: dict,
        execution_result: ToolExecutionResult,
    ) -> None:
        self._record_audit_event(
            record,
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            status=execution_result.status.value,
            message=execution_result.message,
            metadata={"result_keys": sorted(execution_result.result.keys())},
        )

    def _record_execution_failed(
        self,
        record: dict,
        execution_error: ToolExecutionError,
    ) -> None:
        self._record_audit_event(
            record,
            event_type=AuditEventType.TOOL_EXECUTION_FAILED,
            status=ToolExecutionStatus.FAILED.value,
            message=execution_error.error_message,
            metadata={"error_code": execution_error.error_code},
        )

    def _record_audit_event(
        self,
        record: dict,
        *,
        event_type: AuditEventType,
        status: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        conversation_id = str(record.get("conversation_id") or "")
        channel = conversation_id.split(":", 1)[0] if ":" in conversation_id else None
        user_id = conversation_id.split(":", 1)[1] if ":" in conversation_id else None
        self.audit_service.record_event(
            AuditEvent(
                event_type=event_type,
                execution_id=record.get("id"),
                tool_name=record.get("tool_name"),
                provider=record.get("provider"),
                user_id=user_id,
                channel=channel,
                status=status,
                message=message,
                metadata=metadata or {},
            )
        )
