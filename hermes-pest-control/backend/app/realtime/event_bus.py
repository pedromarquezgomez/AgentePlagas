import asyncio
import logging
from app.realtime.contracts import RealtimeEvent

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self, queue: asyncio.Queue):
        self._subscribers.add(queue)

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)

    def publish(self, event: RealtimeEvent):
        # Publicación no bloqueante
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue is full. Skipping event.")

event_bus = EventBus()
