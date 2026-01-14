"""
Simple event bus with signal/slot pattern for service coordination.
"""
from typing import Dict, List, Callable, Any

class EventBus:
    """
    Lightweight event bus for inter-service communication.

    Provides signal/slot pattern with topic support. Services can:
    - Subscribe to events via `on(event, callback)`
    - Unsubscribe via `off(event, callback)`
    - Emit events via `emit(event, data)`
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to an event."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def off(self, event: str, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from an event."""
        if event in self._subscribers:
            self._subscribers[event] = [c for c in self._subscribers[event] if c != callback]

    def emit(self, event: str, data: Any) -> None:
        """Emit an event to all subscribers."""
        for callback in self._subscribers.get(event, []):
            try:
                callback(data)
            except Exception:
                # Log but don't break other subscribers
                pass
