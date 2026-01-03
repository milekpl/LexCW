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
