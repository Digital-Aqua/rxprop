from asyncio import create_task, sleep
from typing import AsyncIterator, Callable
import pytest

import rxprop as rx


async def flush_event_loop():
    # Typically takes two passes to flush our events.
    # But we'll only fail if it takes more than 10 passes.
    for _ in range(10):
        await sleep(0)


class ValueExample:
    @rx.value
    def my_value(self) -> int:
        return 1
    
    @rx.computed
    def my_computed(self) -> int:
        return self.my_value * 10


async def _test_value(
    watch_factory: tuple[
        Callable[[ValueExample], AsyncIterator[int]],
        Callable[[ValueExample], AsyncIterator[int]]
    ]
):
    model = ValueExample()
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
            rx.watchp(x, ValueExample.my_value),
        lambda x:
            rx.watchp(x, ValueExample.my_computed)
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
