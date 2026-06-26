"""SSE Manager Service.

Manages active Server-Sent Events (SSE) connections for users using asyncio queues.
Supports broadcasting to multiple concurrent connections per user.
"""

import asyncio
from typing import Dict, Set
import structlog

logger = structlog.get_logger()


class SSEManager:
    """Manages active per-user asyncio queues for streaming Server-Sent Events."""

    def __init__(self):
        # Maps user_id (string) -> Set of active asyncio.Queue objects
        self._user_queues: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str) -> asyncio.Queue:
        """Create and register a queue for a user's SSE connection."""
        queue = asyncio.Queue()
        async with self._lock:
            if user_id not in self._user_queues:
                self._user_queues[user_id] = set()
            self._user_queues[user_id].add(queue)
            logger.info("sse_client_connected", user_id=user_id, active_connections=len(self._user_queues[user_id]))
        return queue

    async def disconnect(self, user_id: str, queue: asyncio.Queue) -> None:
        """Remove a queue for a user's SSE connection."""
        async with self._lock:
            if user_id in self._user_queues:
                self._user_queues[user_id].discard(queue)
                if not self._user_queues[user_id]:
                    del self._user_queues[user_id]
                logger.info("sse_client_disconnected", user_id=user_id)

    async def send_event(self, user_id: str, event_type: str, data: dict) -> None:
        """Broadcast an event to all active queues registered for a user."""
        async with self._lock:
            queues = self._user_queues.get(user_id)
            if not queues:
                return

            payload = {
                "event": event_type,
                "data": data
            }

            for q in list(queues):
                try:
                    await q.put(payload)
                except Exception as e:
                    logger.error("sse_push_error", user_id=user_id, error=str(e))


# Singleton instance
sse_manager = SSEManager()
