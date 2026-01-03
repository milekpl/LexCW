import pytest
from app.services.event_bus import EventBus

def test_event_bus_emit_and_receive():
    bus = EventBus()
    received = []

    def handler(data):
        received.append(data)

    bus.on('entry_updated', handler)
    bus.emit('entry_updated', {'id': 'test-entry', 'action': 'update'})

    assert len(received) == 1
    assert received[0]['id'] == 'test-entry'

def test_event_bus_unsubscribe():
    bus = EventBus()
    call_count = [0]

    def handler(data):
        call_count[0] += 1

    bus.on('entry_updated', handler)
    bus.off('entry_updated', handler)
    bus.emit('entry_updated', {'id': 'test'})

    assert call_count[0] == 0

def test_event_bus_multiple_handlers():
    bus = EventBus()
    calls = []

    bus.on('entry_updated', lambda d: calls.append('a'))
    bus.on('entry_updated', lambda d: calls.append('b'))

    bus.emit('entry_updated', {})

    assert len(calls) == 2
    assert 'a' in calls
    assert 'b' in calls


def test_emit_on_nonexistent_event():
    """emit on non-existent event should not raise."""
    bus = EventBus()
    bus.emit('nonexistent', {})  # Should not raise


def test_duplicate_subscription_prevented():
    """Same handler should only be added once."""
    bus = EventBus()
    call_count = [0]

    def handler(data):
        call_count[0] += 1

    bus.on('test', handler)
    bus.on('test', handler)  # Second call should be ignored
    bus.emit('test', {})
    assert call_count[0] == 1


def test_unsubscribe_from_nonexistent_event():
    """off on non-existent event should be no-op."""
    bus = EventBus()

    def handler(data):
        pass

    bus.off('nonexistent', handler)  # Should not raise
