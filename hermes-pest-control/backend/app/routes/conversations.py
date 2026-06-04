from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.admin_auth import require_admin_auth
from app.services.firestore_factory import get_firestore_service

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(require_admin_auth)],
)

firestore_service = get_firestore_service()


@router.get("")
async def list_conversations(
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    conversations = await firestore_service.list_documents(
        "conversations",
        limit=limit,
    )
    # Ordenar por fecha de creación descendente si la tienen
    conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return conversations


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    conversation = await firestore_service.get_document(
        "conversations",
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return conversation


@router.get("/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: str,
    limit: int | None = Query(default=100, ge=1, le=500),
) -> list[dict]:
    messages = await firestore_service.list_documents(
        "messages",
        filters={"conversation_id": conversation_id},
    )
    # Ordenar cronológicamente (antiguos primero para el chat feed)
    messages.sort(key=lambda x: x.get("created_at", ""))
    return messages[:limit] if limit is not None else messages


@router.post("/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_conversation_message(
    conversation_id: str,
    payload: dict,
) -> dict:
    conversation = await firestore_service.get_document(
        "conversations",
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    text = payload.get("text")
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text is required.",
        )

    import datetime
    message_data = {
        "id": None,  # Auto-generado por el servicio
        "conversation_id": conversation_id,
        "direction": "outbound",
        "channel": conversation.get("channel", "webchat"),
        "text": text,
        "attachments": [],
        "metadata": {},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    stored = await firestore_service.create_document(
        "messages",
        message_data,
    )
    return stored
