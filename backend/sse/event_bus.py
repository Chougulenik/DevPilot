"""
SSE Event Bus — manages per-session async queues and emits structured JSON events.

Architecture:
  - Each session gets a dedicated asyncio.Queue
  - Producers (agents) push events via emit()
  - The SSE route consumes events via subscribe()
  - Heartbeat task runs every 15s to keep connections alive
  - Last-Event-ID header support for reconnect recovery
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import AsyncGenerator, Optional
from uuid import uuid4

from models.events import BaseEvent, EventType, HeartbeatEvent

logger = logging.getLogger(__name__)

# Sentinel to signal end of stream
_STREAM_DONE = object()


class EventBus:
    """
    Central event bus for routing structured SSE events to connected clients.

    Supports:
    - Multiple subscribers per session (fan-out)
    - Replay buffer: last N events stored per session for reconnect
    - Heartbeat to prevent proxy timeouts
    - Clean teardown on disconnect
    """

    def __init__(self, replay_buffer_size: int = 100, heartbeat_interval: int = 15):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._replay_buffers: dict[str, list[dict]] = defaultdict(list)
        self._replay_buffer_size = replay_buffer_size
        self._heartbeat_interval = heartbeat_interval
        self._sequence_counters: dict[str, int] = defaultdict(int)
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the heartbeat background task."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("EventBus started with heartbeat interval=%ds", self._heartbeat_interval)

    async def stop(self):
        """Stop the heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def emit(self, session_id: str, event: BaseEvent) -> None:
        """
        Emit a structured event to all subscribers of a session.

        Args:
            session_id: Target session identifier
            event: Any BaseEvent subclass instance
        """
        # Assign sequence number
        self._sequence_counters[session_id] += 1
        event.sequence = self._sequence_counters[session_id]

        payload = event.model_dump(mode="json")

        # Store in replay buffer
        buf = self._replay_buffers[session_id]
        buf.append(payload)
        if len(buf) > self._replay_buffer_size:
            buf.pop(0)

        # Fan-out to all connected subscribers
        queues = self._queues.get(session_id, [])
        if not queues:
            logger.debug("No subscribers for session %s, buffering only", session_id)
        for q in queues:
            await q.put(payload)

        logger.debug(
            "Emitted event type=%s seq=%d session=%s",
            event.event_type,
            event.sequence,
            session_id,
        )

    async def emit_done(self, session_id: str) -> None:
        """Signal end-of-stream to all subscribers."""
        for q in self._queues.get(session_id, []):
            await q.put(_STREAM_DONE)

    async def subscribe(
        self,
        session_id: str,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Subscribe to events for a session, yielding SSE-formatted strings.

        Implements:
        - Reconnect replay via Last-Event-ID
        - Heartbeats every N seconds
        - Clean queue cleanup on disconnect

        Yields:
            SSE-formatted data strings (e.g., "data: {...}\\n\\n")
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[session_id].append(queue)

        # Replay missed events if client reconnected with Last-Event-ID
        if last_event_id:
            await self._replay_missed(session_id, last_event_id, queue)

        logger.info("Client subscribed to session %s", session_id)
        try:
            while True:
                try:
                    # Wait for the next event with a timeout for heartbeat
                    payload = await asyncio.wait_for(
                        queue.get(), timeout=self._heartbeat_interval
                    )
                except asyncio.TimeoutError:
                    # Send heartbeat comment (not a data event, just keeps connection alive)
                    yield f": heartbeat {datetime.utcnow().isoformat()}Z\n\n"
                    continue

                if payload is _STREAM_DONE:
                    logger.info("Stream done for session %s", session_id)
                    break

                event_id = payload.get("event_id", str(uuid4()))
                event_type = payload.get("event_type", "unknown")
                data = json.dumps(payload, ensure_ascii=False)
                yield f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"

        except asyncio.CancelledError:
            logger.info("Client disconnected from session %s", session_id)
        finally:
            # Clean up subscriber queue
            queues = self._queues.get(session_id, [])
            if queue in queues:
                queues.remove(queue)
            if not queues and session_id in self._queues:
                del self._queues[session_id]

    async def _replay_missed(
        self, session_id: str, last_event_id: str, queue: asyncio.Queue
    ) -> None:
        """Replay events that occurred after the given last_event_id."""
        buf = self._replay_buffers.get(session_id, [])
        found = False
        for event in buf:
            if found:
                await queue.put(event)
            if event.get("event_id") == last_event_id:
                found = True
        if not found:
            # If ID not found, replay entire buffer (safe fallback)
            for event in buf:
                await queue.put(event)
        logger.debug("Replayed %d buffered events for session %s", len(buf), session_id)

    async def _heartbeat_loop(self) -> None:
        """Periodically emit heartbeat events to prevent proxy timeouts."""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            for session_id in list(self._queues.keys()):
                try:
                    hb = HeartbeatEvent(
                        session_id=session_id,
                        connected_clients=len(self._queues.get(session_id, [])),
                    )
                    await self.emit(session_id, hb)
                except Exception as exc:
                    logger.warning("Heartbeat error for session %s: %s", session_id, exc)

    def get_replay_buffer(self, session_id: str) -> list[dict]:
        """Return stored events for a session (for REST state fetch)."""
        return list(self._replay_buffers.get(session_id, []))

    def active_session_ids(self) -> list[str]:
        return list(self._queues.keys())


# Global singleton event bus (initialized at app startup)
event_bus = EventBus()
