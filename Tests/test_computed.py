import gc, weakref
from asyncio import create_task
from typing import AsyncIterator, Callable

import pytest

import rxprop as rx

from utils import flush_event_loop


class ComputedExample:
    @rx.value
    def my_value(self) -> int:
        return 1
    
    @rx.computed
    def my_computed(self) -> int:
        return self.my_value * 10


async def _test_value(
    watch_factory: tuple[
        Callable[[ComputedExample], AsyncIterator[int]],
        Callable[[ComputedExample], AsyncIterator[int]]
    ]
):
    model = ComputedExample()
    received_values: list[int] = []
    received_computed: list[int] = []

    # Watch
    async def watch_value():
        nonlocal received_values
        async for value in watch_factory[0](model):
            print(f"Received value: {value}")
            received_values.append(value)
            if len(received_values) >= 3:
                break
    task_value = create_task(watch_value())

    async def watch_computed():
        nonlocal received_computed
        async for value in watch_factory[1](model):
            print(f"Received computed: {value}")
            received_computed.append(value)
            if len(received_computed) >= 3:
                break
    task_computed = create_task(watch_computed())
    
    # Check initial value
    assert model.my_value == 1
    assert model.my_computed == 10
    await flush_event_loop()
    assert received_values == [1]
    assert received_computed == [10]
    
    # Check update
    model.my_value = 2
    assert model.my_value == 2
    assert model.my_computed == 20
    await flush_event_loop()
    assert received_values == [1, 2]
    assert received_computed == [10, 20]

    # Check another update
    model.my_value = 3
    assert model.my_value == 3
    assert model.my_computed == 30
    await flush_event_loop()
    assert received_values == [1, 2, 3]
    assert received_computed == [10, 20, 30]
    
    # Verify processing
    await flush_event_loop()
    assert task_value.done()
    assert not task_value.exception()
    assert task_computed.done()
    assert not task_computed.exception()


@pytest.mark.asyncio
async def test_computed_watchf():
    await _test_value((
        lambda x:
            rx.watchf(lambda: x.my_value),
        lambda x:
            rx.watchf(lambda: x.my_computed)
    ))

@pytest.mark.asyncio
async def test_computed_watchp_property():
    await _test_value((
        lambda x:
            rx.watchp(x, ComputedExample.my_value),
        lambda x:
            rx.watchp(x, ComputedExample.my_computed)
    ))

@pytest.mark.asyncio
async def test_computed_watchp_string():
    await _test_value(
        (
            lambda x:
                rx.watchp(x, 'my_value'),
            lambda x:
                rx.watchp(x, 'my_computed')
        )
    )

@pytest.mark.asyncio
async def test_source_not_kept_alive():
    # Given a computed property that depends on a source,
    # when the source goes out of scope,
    # the source is not kept alive.
    # SOMEWHAT CONTRIVED:
    # Normally, a class would hold its dependencies strongly;
    # so for the sake of this test, we'll use weak references.

    class ModelA:
        @rx.value
        def a(self) -> int:
            return 0
        
    class ModelB:
        @rx.value
        def b(self) -> int:
            return 1
        
    class ModelC:
        def __init__(self, model_a: ModelA, model_b: ModelB):
            self.a = weakref.ref(model_a)
            self.b = weakref.ref(model_b)

        @rx.computed
        def c(self) -> int:
            if self.a().a:         # type: ignore
                return self.a().a  # type: ignore
            if not self.b():
                raise Exception(
                    "Attempting to recalculate using model_b after it was GC'd."
                )
            return self.b().b      # type: ignore

    model_a = ModelA()
    model_b = ModelB()
    model_c = ModelC(model_a, model_b)

    assert model_a.a == 0
    assert model_b.b == 1
    assert model_c.c == 1
    # Should be bound to both model_a and model_b
    # ('if' and 'then' respectively).

    received_computed: list[int] = []
    async def watch_computed():
        nonlocal received_computed
        async for value in rx.watchp(model_c, ModelC.c):
            print(f"Received computed: {value}")
            received_computed.append(value)
            if len(received_computed) >= 3:
                break
    task_computed = create_task(watch_computed())

    await flush_event_loop()
    assert received_computed == [1] # Initial value, value of b

    model_b.b = 2
    assert model_c.c == 2
    await flush_event_loop()
    assert received_computed == [1, 2]

    # Remove model_b from the binding;
    # it should be GC'd due to no-keepalive feature,
    # (because we lose our only way to trigger it).
    weak_model_b = weakref.ref(model_b)
    model_b = None
    gc.collect()
    assert weak_model_b() is None

    # No notifications should have been triggered.
    assert model_c.c == 2 # hit cache, no recompute (else error thrown)
    await flush_event_loop()
    assert received_computed == [1, 2]

    model_a.a = 3 # should trigger cache invalidation and queue a notification
    assert model_c.c == 3 # should recalculate dirty cache
    await flush_event_loop()
    assert received_computed == [1, 2, 3]

    task_computed.cancel()
