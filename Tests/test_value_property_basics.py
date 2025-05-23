import rxprop
import asyncio
from typing import List, AsyncIterator, TypeVar

_T = TypeVar('_T')

_default_factory_call_count = 0

class ModelWithValue:
    @rxprop.value
    def val(self) -> int:
        return 100

    @rxprop.value
    def val_str(self) -> str:
        return "default_string"

class ModelWithDefaultFactory:
    @rxprop.value
    def val_with_factory(self) -> int:
        global _default_factory_call_count
        _default_factory_call_count += 1
        return 10

class ModelForNotifications:
    @rxprop.value
    def data(self) -> int:
        return 0

async def _consume_notifications(watch_iterator: AsyncIterator[_T], received_values_list: List[_T], notification_event: asyncio.Event | None = None):
    async for value in watch_iterator:
        received_values_list.append(value)
        if notification_event:
            notification_event.set()

def test_access_when_instance_created_then_returns_default_value():
    """Tests that accessing a value property on a new instance returns the default value."""
    instance = ModelWithValue()
    assert instance.val == 100
    assert instance.val_str == "default_string"

def test_set_value_then_stores_new_value():
    """Tests that setting a value property stores the new value."""
    instance = ModelWithValue()
    instance.val = 200
    assert instance.val == 200

    instance.val_str = "new_string"
    assert instance.val_str == "new_string"

def test_access_multiple_times_then_returns_consistent_value():
    """Tests that accessing a value property multiple times returns the same stored value."""
    instance = ModelWithValue()
    assert instance.val == 100
    assert instance.val == 100 # Access again

    instance.val = 50
    assert instance.val == 50
    assert instance.val == 50 # Access again after change 

def test_first_access_then_default_factory_called_once():
    """Tests that the default value factory is called exactly once on first access."""
    global _default_factory_call_count
    _default_factory_call_count = 0 # Reset counter for this test

    instance = ModelWithDefaultFactory()
    assert _default_factory_call_count == 0 # Not called yet

    assert instance.val_with_factory == 10 # First access
    assert _default_factory_call_count == 1

    _ = instance.val_with_factory # Access again
    assert _default_factory_call_count == 1 # Still 1, not called again

def test_set_before_first_access_then_default_factory_not_called():
    """Tests that the default value factory is NOT called if the property is set before first access."""
    global _default_factory_call_count
    _default_factory_call_count = 0 # Reset counter for this test

    instance = ModelWithDefaultFactory()
    instance.val_with_factory = 20 # Set before first access

    assert _default_factory_call_count == 0
    assert instance.val_with_factory == 20
    assert _default_factory_call_count == 0 # Still 0, factory should not have been called 

async def test_set_new_value_then_watcher_notified():
    """Tests that a watcher is notified with the new value when the property changes."""
    instance = ModelForNotifications()
    instance.data = 42 # Initial value for watcher

    received_values: List[int] = []
    notification_event = asyncio.Event()

    # Watcher gets current value first
    watch_iterator: AsyncIterator[int] = rxprop.watch(instance, ModelForNotifications.data)
    consumer_task = asyncio.create_task(
        _consume_notifications(watch_iterator, received_values, notification_event)
    )
    
    await asyncio.sleep(0) # Allow consumer to start and get initial value
    assert received_values == [42]

    notification_event.clear()
    instance.data = 100
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher was not notified in time after value changed"
    
    assert received_values == [42, 100]
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

async def test_set_same_value_then_watcher_not_notified():
    """Tests that a watcher is NOT notified if the property is set to its current value."""
    instance = ModelForNotifications()
    instance.data = 77 # Initial value for watcher

    received_values: List[int] = []
    notification_event = asyncio.Event()

    watch_iterator: AsyncIterator[int] = rxprop.watch(instance, ModelForNotifications.data)
    consumer_task = asyncio.create_task(
        _consume_notifications(watch_iterator, received_values, notification_event)
    )
    
    await asyncio.sleep(0) # Allow consumer to start and get initial value
    assert received_values == [77]
    assert len(received_values) == 1

    notification_event.clear() # Clear after initial value
    instance.data = 77 # Set to same value

    notified = False
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.01) # Short timeout
        notified = True
    except asyncio.TimeoutError:
        notified = False # Expected: watcher should not be notified
    
    assert not notified, "Watcher was notified even when value did not change"
    assert received_values == [77] # Should still only contain the initial value

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass 