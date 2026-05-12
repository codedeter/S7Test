import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DATA_RECEIVED = "data.received"
    DATA_STORED = "data.stored"
    FAULT_DETECTED = "fault.detected"
    ANOMALY_DETECTED = "anomaly.detected"


@dataclass
class Event:
    event_type: EventType
    timestamp: float
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'timestamp': self.timestamp,
            'payload': self.payload,
            'correlation_id': self.correlation_id
        }


class EventHandler:
    def __init__(self, handler: Callable, async_mode: bool = False):
        self.handler = handler
        self.async_mode = async_mode


class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._event_queue = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: EventType, handler: Callable, async_mode: bool = False):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(EventHandler(handler, async_mode))

    def publish(self, event: Event):
        asyncio.create_task(self._event_queue.put(event))

    async def _process_events(self):
        while self._running:
            event = await self._event_queue.get()
            await self._dispatch_event(event)
            self._event_queue.task_done()

    async def _dispatch_event(self, event: Event):
        handlers = self._subscribers.get(event.event_type, [])

        for handler in handlers:
            try:
                if handler.async_mode:
                    await handler.handler(event)
                else:
                    handler.handler(event)
            except Exception as e:
                print(f"Failed to handle event {event.event_type}: {e}")

    def start(self):
        self._running = True
        asyncio.create_task(self._process_events())

    def stop(self):
        self._running = False


event_bus = EventBus()