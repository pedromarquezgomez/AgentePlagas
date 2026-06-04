import asyncio
import logging
from fastapi import APIRouter, Depends, Query, Request, Header
from fastapi.responses import StreamingResponse
from app.dependencies.admin_auth import require_admin_user, AdminUserContext
from app.realtime.event_bus import event_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["realtime"])

async def require_sse_auth(
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> AdminUserContext:
    if token and not authorization:
        authorization = f"Bearer {token}"
    return await require_admin_user(authorization, x_admin_api_key)

@router.get("/stream")
async def events_stream(
    request: Request,
    auth_context: AdminUserContext = Depends(require_sse_auth)
):
    async def event_generator():
        # Cola asíncrona para recibir eventos del EventBus
        queue = asyncio.Queue(maxsize=100)
        event_bus.subscribe(queue)
        logger.info("New client connected to Event Stream. Auth UID: %s", auth_context.uid)
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("Client disconnected from Event Stream. Auth UID: %s", auth_context.uid)
                    break
                try:
                    # Esperar evento con timeout de 20s para enviar un keep-alive
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    # Enviar keepalive
                    yield ": keepalive\n\n"
        except Exception as exc:
            logger.error("Error in Event Stream generator: %s", exc)
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Deshabilitar almacenamiento en caché en proxies como Nginx
        }
    )
