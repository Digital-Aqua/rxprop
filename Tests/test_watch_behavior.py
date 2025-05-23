import rxprop
import asyncio
from typing import List, AsyncIterator, TypeVar

_T = TypeVar('_T')

class ModelForWatchValue:
    @rxprop.value
    def my_data(self) -> int:
        return 123

    @rxprop.value
    def str_data(self) -> str:
        return "initial"

async def _consume_for_test(iterator: AsyncIterator[_T], max_items: int = 0) -> List[_T]:
    """Consumes from an async iterator, optionally up to max_items, returns list."""
    results: List[_T] = []
    count = 0
    async for item in iterator: # item is of type _T
        results.append(item)
        count += 1
        if max_items > 0 and count >= max_items:
            break
    return results

def test_watch_value_returns_async_iterator():
    """Tests that rxprop.watch on a value property returns an AsyncIterator."""
    instance = ModelForWatchValue()
    watcher = rxprop.watch(instance, ModelForWatchValue.my_data)
    
    assert hasattr(watcher, '__aiter__'), "Watcher does not have __aiter__"
    assert hasattr(watcher, '__anext__'), "Watcher does not have __anext__"
    
    # More robust check if using Python 3.9+ type hints for AsyncIterator
    # For now, checking protocol is good enough.
    # from collections.abc import AsyncIterator as ABCAsyncIterator
    # assert isinstance(watcher, ABCAsyncIterator)

async def test_watch_value_yields_current_value_immediately():
    """Tests that rxprop.watch on a value property yields the current value immediately."""
    instance = ModelForWatchValue()
    instance.my_data = 456 # Set a specific current value

    # Consume only the first item
    # watcher = rxprop.watch(instance, ModelForWatchValue.my_data)
    # first_value = await asyncio.wait_for(watcher.__anext__(), timeout=0.1)
    # A more robust way using the helper for cleaner task management:
    consumer_task = asyncio.create_task(_consume_for_test(rxprop.watch(instance, ModelForWatchValue.my_data), max_items=1))
    
    try:
        results = await asyncio.wait_for(consumer_task, timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher did not yield initial value in time"
        results = [] # for type checker
    
    assert results == [456]

async def test_watch_value_yields_new_value_on_change():
    """Tests that watcher on value property yields new value when it changes."""
    instance = ModelForWatchValue()
    instance.my_data = 10

    received_values: List[int] = []
    notification_event = asyncio.Event()
    
    async def consumer():
        async for val in rxprop.watch(instance, ModelForWatchValue.my_data):
            received_values.append(val)
            notification_event.set()
            if len(received_values) >= 2: # Expect initial + 1 change
                break

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0) # Let consumer get initial value (10)
    assert received_values == [10]

    notification_event.clear()
    instance.my_data = 20

    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher did not yield changed value in time"
    
    assert received_values == [10, 20]
    # Ensure task finishes if not already broken by len check
    if not consumer_task.done():
        consumer_task.cancel()
        try: await consumer_task
        except asyncio.CancelledError: pass

async def test_watch_value_multiple_quick_changes_yields_latest():
    """Tests that for multiple quick changes, the watcher yields the latest value (not necessarily all intermediate)."""
    # This test assumes that not all intermediate values are guaranteed, as per stubs.
    # It primarily checks that the *final* value in a sequence of rapid changes is received.
    instance = ModelForWatchValue()
    instance.my_data = 1 # Initial value for watcher

    received_values: List[int] = []
    notification_event = asyncio.Event()
    # We expect initial value, then the *latest* after a burst of changes.

    async def consumer():
        async for val in rxprop.watch(instance, ModelForWatchValue.my_data):
            received_values.append(val)
            if len(received_values) >= 2: # Expect initial value, then the one after burst
                 notification_event.set()
                 # If we get more, that's fine, but we only wait for the second significant one.
            if len(received_values) >= 10: # Safety break if too many notifications somehow
                break

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0) # Allow consumer to get initial value (1)
    assert received_values == [1]

    # Rapid changes
    instance.my_data = 2
    instance.my_data = 3
    instance.my_data = 4 # This is the latest value we expect to see after the initial one.

    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1) 
    except asyncio.TimeoutError:
        # This might happen if notifications are heavily debounced/coalesced.
        # The critical part is that the *eventual* state reflects the last change.
        pass # Continue to assert final state

    # Check that the list contains the initial value and the final value.
    # Intermediate values (2, 3) may or may not be present.
    assert 1 in received_values
    assert 4 in received_values
    assert received_values[0] == 1 # First one must be the initial value
    assert received_values[-1] == 4 # Last one received must be the final set value
    
    # To be very specific about the plan: "yields the latest value"
    # This means after the burst, the *next* notification should be 4.
    # The list received_values should be [1, 4] if only latest is guaranteed after initial.
    # If intermediate are possible, it could be [1, 2, 3, 4] or [1, 2, 4] or [1, 3, 4] or [1, 4].
    # The stub says "NOT guaranteed to yield intermediate values", so [1, 4] is a valid expectation.
    # We check that the *last* value received is indeed the *last* value set.

    if not consumer_task.done():
        consumer_task.cancel()
        try: await consumer_task
        except asyncio.CancelledError: pass 

class ModelForWatchComputed:
    def __init__(self):
        self._comp_call_count = 0

    @rxprop.value
    def source1(self) -> int:
        return 10

    @rxprop.value
    def source2(self) -> int:
        return 20

    @rxprop.computed
    def computed_val(self) -> int:
        self._comp_call_count += 1
        return self.source1 + self.source2
    
    def get_computation_count(self) -> int:
        return self._comp_call_count

def test_watch_computed_returns_async_iterator():
    """Tests that rxprop.watch on a computed property returns an AsyncIterator."""
    instance = ModelForWatchComputed()
    watcher = rxprop.watch(instance, ModelForWatchComputed.computed_val)
    assert hasattr(watcher, '__aiter__')
    assert hasattr(watcher, '__anext__')

async def test_watch_computed_yields_current_value_immediately():
    """Tests that rxprop.watch on a computed property yields its current value immediately."""
    instance = ModelForWatchComputed()
    instance.source1 = 7
    instance.source2 = 3
    # computed_val should be 10

    consumer_task = asyncio.create_task(_consume_for_test(rxprop.watch(instance, ModelForWatchComputed.computed_val), max_items=1))
    try:
        results = await asyncio.wait_for(consumer_task, timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher (computed) did not yield initial value in time"
        results = []
    assert results == [10]

async def test_watch_computed_yields_new_value_on_dependency_change():
    """Tests watcher on computed property yields new value when dependency changes."""
    instance = ModelForWatchComputed()
    instance.source1 = 5 # Initial computed_val = 5 + 20 = 25

    received_values: List[int] = []
    notification_event = asyncio.Event()
    
    async def consumer():
        async for val in rxprop.watch(instance, ModelForWatchComputed.computed_val):
            received_values.append(val)
            notification_event.set()
            if len(received_values) >= 2: # Expect initial + 1 change
                break

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0) # Let consumer get initial value (25)
    assert received_values == [25]

    notification_event.clear()
    instance.source1 = 15 # computed_val becomes 15 + 20 = 35

    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher (computed) did not yield changed value in time"
    
    assert received_values == [25, 35]
    if not consumer_task.done():
        consumer_task.cancel()
        try: 
            await consumer_task
        except asyncio.CancelledError: 
            pass 

class ModelForWatchByName:
    @rxprop.value
    def my_prop(self) -> int:
        return 100

    @rxprop.computed
    def my_computed_prop(self) -> str:
        return f"Value: {self.my_prop}"

async def test_watch_value_property_by_name_behaves_same_as_direct():
    """Tests watching a value property by name string yields same results as direct object watch."""
    instance = ModelForWatchByName()
    instance.my_prop = 200 # Initial value

    # Watch by property object
    received_direct: List[int] = []
    direct_event = asyncio.Event()
    async def consumer_direct():
        async for val in rxprop.watch(instance, ModelForWatchByName.my_prop):
            received_direct.append(val)
            direct_event.set()
            if len(received_direct) >=2: break
    direct_task = asyncio.create_task(consumer_direct())
    await asyncio.sleep(0)
    direct_event.clear()
    instance.my_prop = 250
    try: await asyncio.wait_for(direct_event.wait(), timeout=0.1)
    except asyncio.TimeoutError: assert False, "Direct watch failed to notify"
    if not direct_task.done(): direct_task.cancel(); await asyncio.gather(direct_task, return_exceptions=True)

    # Watch by property name
    instance.my_prop = 300 # Reset for name watch
    received_by_name: List[int] = []
    name_event = asyncio.Event()
    async def consumer_by_name():
        async for val in rxprop.watch(instance, "my_prop"):
            received_by_name.append(val)
            name_event.set()
            if len(received_by_name) >= 2: break
    name_task = asyncio.create_task(consumer_by_name())
    await asyncio.sleep(0)
    name_event.clear()
    instance.my_prop = 350
    try: await asyncio.wait_for(name_event.wait(), timeout=0.1)
    except asyncio.TimeoutError: assert False, "Name watch failed to notify"
    if not name_task.done(): name_task.cancel(); await asyncio.gather(name_task, return_exceptions=True)
    
    # Compare results (initial value + one change)
    assert received_direct == [200, 250]
    assert received_by_name == [300, 350]
    # The core idea is that it *works* and gets the same sequence of events for same changes.
    # Here we tested they both get initial + one change.

async def test_watch_computed_property_by_name_behaves_same_as_direct():
    """Tests watching a computed property by name string yields same results as direct object watch."""
    instance = ModelForWatchByName()
    instance.my_prop = 10 # Initial: my_computed_prop = "Value: 10"

    received_direct: List[str] = []
    direct_event = asyncio.Event()
    async def consumer_direct():
        async for val in rxprop.watch(instance, ModelForWatchByName.my_computed_prop):
            received_direct.append(val)
            direct_event.set()
            if len(received_direct) >=2: break
    direct_task = asyncio.create_task(consumer_direct())
    await asyncio.sleep(0)
    direct_event.clear()
    instance.my_prop = 20 # my_computed_prop = "Value: 20"
    try: await asyncio.wait_for(direct_event.wait(), timeout=0.1)
    except asyncio.TimeoutError: assert False, "Direct computed watch failed to notify"
    if not direct_task.done(): direct_task.cancel(); await asyncio.gather(direct_task, return_exceptions=True)

    instance.my_prop = 30 # Reset for name watch: my_computed_prop = "Value: 30"
    received_by_name: List[str] = []
    name_event = asyncio.Event()
    async def consumer_by_name():
        async for val in rxprop.watch(instance, "my_computed_prop"):
            received_by_name.append(val)
            name_event.set()
            if len(received_by_name) >= 2: break
    name_task = asyncio.create_task(consumer_by_name())
    await asyncio.sleep(0)
    name_event.clear()
    instance.my_prop = 40 # my_computed_prop = "Value: 40"
    try: await asyncio.wait_for(name_event.wait(), timeout=0.1)
    except asyncio.TimeoutError: assert False, "Name computed watch failed to notify"
    if not name_task.done(): name_task.cancel(); await asyncio.gather(name_task, return_exceptions=True)

    assert received_direct == ["Value: 10", "Value: 20"]
    assert received_by_name == ["Value: 30", "Value: 40"]

async def test_watch_non_existent_property_by_name_raises_error():
    """Tests that watching a non-existent property by name raises AttributeError."""
    instance = ModelForWatchByName()
    raised_error = False
    try:
        # Attempt to iterate to trigger the error if it's lazy
        async for _ in rxprop.watch(instance, "non_existent_prop"):
            pass # pragma: no cover
    except AttributeError:
        raised_error = True
    except Exception as e:
        assert False, f"Expected AttributeError, got {type(e).__name__}: {e}"
    assert raised_error, "AttributeError not raised for non-existent property name watch."

async def test_watch_iterator_exhaustion_removes_handler():
    """Tests that when a watch iterator is exhausted, the handler is removed."""
    instance = ModelForWatchValue()
    instance.my_data = 1 # Initial

    received_values: List[int] = []
    notification_event = asyncio.Event() # For synchronizing the *first few* notifications

    # Consumer that will break after receiving two items (initial + one change)
    async def limited_consumer():
        items_to_receive = 2
        items_received = 0
        async for val in rxprop.watch(instance, ModelForWatchValue.my_data):
            received_values.append(val)
            items_received += 1
            notification_event.set() # Signal each item received for test sync
            notification_event.clear() # Reset for next potential item
            if items_received >= items_to_receive:
                break # Exhaust the watcher by breaking the loop
    
    consumer_task = asyncio.create_task(limited_consumer())

    # --- First phase: get initial value --- 
    try: 
        await asyncio.wait_for(notification_event.wait(), timeout=0.1) # Wait for 1st item (initial value)
    except asyncio.TimeoutError: 
        assert False, "Watcher did not yield initial value"
    assert received_values == [1]

    # --- Second phase: trigger one change and receive it --- 
    instance.my_data = 2 # Change value
    try: 
        await asyncio.wait_for(notification_event.wait(), timeout=0.1) # Wait for 2nd item
    except asyncio.TimeoutError: 
        assert False, "Watcher did not yield second value after change"
    assert received_values == [1, 2]

    # At this point, the consumer loop should have broken and exited.
    # Wait for the consumer task to actually finish to ensure loop is exited.
    try:
        await asyncio.wait_for(consumer_task, timeout=0.1)
    except asyncio.TimeoutError:
        # This should not happen if the loop correctly breaks
        consumer_task.cancel() # Force cancel if stuck
        await asyncio.gather(consumer_task, return_exceptions=True)
        assert False, "Limited consumer task did not finish as expected."

    # --- Third phase: Change property again AFTER watcher should be closed --- 
    instance.my_data = 3 # Change value again
    
    # Give some time for any stray notification to (incorrectly) arrive
    await asyncio.sleep(0.05) 

    # Assert that no new values were received, meaning the handler was removed.
    assert received_values == [1, 2], \
        f"Watcher received more values after loop exhaustion. Expected [1,2], got {received_values}" 