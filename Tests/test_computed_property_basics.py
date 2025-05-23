import rxprop
import asyncio
from typing import List, AsyncIterator, TypeVar

_T = TypeVar('_T')

class ModelWithComputed:
    @rxprop.value
    def source_val1(self) -> int:
        return 10

    @rxprop.value
    def source_val2(self) -> int:
        return 5

    @rxprop.computed
    def computed_sum(self) -> int:
        return self.source_val1 + self.source_val2

    @rxprop.computed
    def computed_string_concat(self) -> str:
        return str(self.source_val1) + "-" + str(self.source_val2)


def test_create_instance_then_computed_returns_correct_initial_value():
    """Tests that a computed property returns the correct initial value based on dependencies."""
    instance = ModelWithComputed()
    assert instance.computed_sum == 15 # 10 + 5
    assert instance.computed_string_concat == "10-5"

    instance.source_val1 = 7
    instance.source_val2 = 3
    assert instance.computed_sum == 10 # 7 + 3
    assert instance.computed_string_concat == "7-3"

    instance2 = ModelWithComputed()
    assert instance2.computed_sum == 15 # Default 10 + 5
    instance2.source_val1 = 1
    assert instance2.computed_sum == 6 # 1 + 5
    assert instance2.computed_string_concat == "1-5"

_computed_sum_call_count = 0

class ModelForRecomputation:
    def __init__(self):
        self.reset_counts()

    def reset_counts(self):
        global _computed_sum_call_count
        _computed_sum_call_count = 0

    @rxprop.value
    def dep1(self) -> int:
        return 1

    @rxprop.value
    def dep2(self) -> int:
        return 2

    @rxprop.value
    def unrelated_val(self) -> int:
        return 100

    @rxprop.computed
    def computed_sum_tracked(self) -> int:
        global _computed_sum_call_count
        _computed_sum_call_count += 1
        return self.dep1 + self.dep2

def test_dependency_change_then_computed_recalculated():
    instance = ModelForRecomputation()
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    instance.dep1 = 5
    assert instance.computed_sum_tracked == 7
    assert _computed_sum_call_count == 2
    instance.dep2 = 10
    assert instance.computed_sum_tracked == 15
    assert _computed_sum_call_count == 3

def test_multiple_dependencies_change_then_computed_recalculated():
    instance = ModelForRecomputation()
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    instance.dep1 = 10
    assert instance.computed_sum_tracked == 12
    assert _computed_sum_call_count == 2
    instance.dep2 = 20
    assert instance.computed_sum_tracked == 30
    assert _computed_sum_call_count == 3

def test_non_dependency_change_then_computed_not_recalculated():
    instance = ModelForRecomputation()
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    instance.unrelated_val = 200
    assert instance.computed_sum_tracked == 3 
    assert _computed_sum_call_count == 1

def test_access_multiple_times_with_no_dependency_change_then_computation_cached():
    instance = ModelForRecomputation()
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1

def test_access_after_dependency_change_then_computation_recalculated():
    instance = ModelForRecomputation()
    assert instance.computed_sum_tracked == 3
    assert _computed_sum_call_count == 1
    instance.dep1 = 10
    assert instance.computed_sum_tracked == 12
    assert _computed_sum_call_count == 2
    assert instance.computed_sum_tracked == 12
    assert _computed_sum_call_count == 2 

async def _consume_notifications_computed(watch_iterator: AsyncIterator[_T], received_values_list: List[_T], notification_event: asyncio.Event | None = None):
    async for value in watch_iterator:
        received_values_list.append(value)
        if notification_event:
            notification_event.set()

class ModelForComputedNotifications:
    def __init__(self):
        self.reset_counts()
        self._computation_count = 0

    def reset_counts(self):
        self._computation_count = 0

    @rxprop.value
    def dep_a(self) -> int:
        return 1

    @rxprop.value
    def dep_b(self) -> int:
        return 10

    @rxprop.computed
    def computed_prop(self) -> int:
        self._computation_count += 1
        return self.dep_a * self.dep_b

    @rxprop.value
    def dep_c(self) -> int:
        return 5
    
    @rxprop.value
    def dep_d(self) -> int:
        return -5

    @rxprop.computed
    def computed_eval_positive_sum(self) -> bool:
        return (self.dep_c + self.dep_d) > 0

async def test_dependency_change_causes_computed_change_then_watcher_notified():
    instance = ModelForComputedNotifications()
    instance.dep_a = 2
    instance.dep_b = 3
    received_values: List[int] = []
    notification_event = asyncio.Event()
    watch_iterator = rxprop.watch(instance, ModelForComputedNotifications.computed_prop)
    consumer_task = asyncio.create_task(
        _consume_notifications_computed(watch_iterator, received_values, notification_event)
    )
    await asyncio.sleep(0)
    assert received_values == [6]
    notification_event.clear()
    instance.dep_a = 4
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher was not notified after computed value changed"
    assert received_values == [6, 12]
    consumer_task.cancel()
    try: await consumer_task
    except asyncio.CancelledError: pass

async def test_dependency_change_no_computed_value_change_then_watcher_not_notified():
    instance = ModelForComputedNotifications()
    assert instance.computed_eval_positive_sum is False
    received_values: List[bool] = []
    notification_event = asyncio.Event()
    watch_iterator = rxprop.watch(instance, ModelForComputedNotifications.computed_eval_positive_sum)
    consumer_task = asyncio.create_task(
        _consume_notifications_computed(watch_iterator, received_values, notification_event)
    )
    await asyncio.sleep(0)
    assert received_values == [False]
    notification_event.clear()
    instance.dep_c = 6 
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher not notified after value changed from False to True"
    assert received_values == [False, True]
    notification_event.clear()
    instance.dep_c = 7
    notified_again = False
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.05)
        notified_again = True
    except asyncio.TimeoutError:
        notified_again = False
    assert not notified_again, "Watcher was notified even when computed value did not change"
    assert received_values == [False, True]
    consumer_task.cancel()
    try: await consumer_task
    except asyncio.CancelledError: pass

_computed1_call_count = 0
_computed2_call_count = 0

class ModelWithNestedComputed:
    def __init__(self):
        self.reset_counts()

    def reset_counts(self):
        global _computed1_call_count, _computed2_call_count
        _computed1_call_count = 0
        _computed2_call_count = 0

    @rxprop.value
    def base_val(self) -> int:
        return 1

    @rxprop.computed
    def computed1(self) -> int:
        global _computed1_call_count
        _computed1_call_count += 1
        return self.base_val * 10

    @rxprop.computed
    def computed2(self) -> int:
        global _computed2_call_count
        _computed2_call_count += 1
        return self.computed1 + 5

async def test_nested_computed_properties_recompute_and_notify():
    instance = ModelWithNestedComputed()
    assert instance.computed2 == 15
    assert _computed1_call_count == 1
    assert _computed2_call_count == 1
    instance.reset_counts()
    received_values: List[int] = []
    notification_event = asyncio.Event()
    watch_iterator = rxprop.watch(instance, ModelWithNestedComputed.computed2)
    consumer_task = asyncio.create_task(
        _consume_notifications_computed(watch_iterator, received_values, notification_event)
    )
    await asyncio.sleep(0)
    assert received_values == [15]
    assert _computed1_call_count == 1 
    assert _computed2_call_count == 1
    notification_event.clear()
    instance.reset_counts()
    instance.base_val = 2
    try:
        await asyncio.wait_for(notification_event.wait(), timeout=0.1)
    except asyncio.TimeoutError:
        assert False, "Watcher on computed2 was not notified after base_val change"
    assert _computed1_call_count >= 1, "computed1 should have been re-evaluated"
    assert _computed2_call_count >= 1, "computed2 should have been re-evaluated"
    assert received_values == [15, 25]
    assert instance.computed2 == 25
    consumer_task.cancel()
    try: await consumer_task
    except asyncio.CancelledError: pass

def test_set_computed_property_then_raises_error():
    """Tests that attempting to set a computed property (without a setter) raises an error."""
    instance = ModelWithComputed() # Uses the simple ModelWithComputed
    
    raised_error = False
    try:
        instance.computed_sum = 100 # Attempt to set
    except AttributeError:
        raised_error = True
    except Exception as e:
        assert False, f"Expected AttributeError, but got {type(e).__name__}: {e}"
        
    assert raised_error, "AttributeError was not raised when setting a computed property."

    # Also test with another computed property from a different model
    instance_recompute = ModelForRecomputation()
    raised_error_recompute = False
    try:
        instance_recompute.computed_sum_tracked = 200
    except AttributeError:
        raised_error_recompute = True
    except Exception as e:
        assert False, f"Expected AttributeError for ModelForRecomputation, but got {type(e).__name__}: {e}"
    assert raised_error_recompute, "AttributeError was not raised for ModelForRecomputation.computed_sum_tracked." 