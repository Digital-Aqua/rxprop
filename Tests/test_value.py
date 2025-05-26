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


async def _test_value(
    watch_factory: Callable[[ValueExample], AsyncIterator[int]]
):
    model = ValueExample()
    received_values: list[int] = []

    # Watch
    async def watch_value():
        nonlocal received_values
        async for value in watch_factory(model):
            print(f"Received value: {value}")
            received_values.append(value)
            if len(received_values) >= 3:
                break
    task = create_task(watch_value())
    
    # Check initial value
    assert model.my_value == 1
    await flush_event_loop()
    assert received_values == [1]
    
    # Check update
    model.my_value = 2
    assert model.my_value == 2
    await flush_event_loop()
    assert received_values == [1, 2]

    # Check another update
    model.my_value = 3
    assert model.my_value == 3
    await flush_event_loop()
    assert received_values == [1, 2, 3]
    
    # Verify processing
    await flush_event_loop()
    assert task.done()
    assert not task.exception()


@pytest.mark.asyncio
async def test_value_watchf():
    await _test_value(
        lambda x:
            rx.watchf(lambda: x.my_value)
    )

@pytest.mark.asyncio
async def test_value_watchp_property():
    await _test_value(
        lambda x:
            rx.watchp(x, ValueExample.my_value)
    )

@pytest.mark.asyncio
async def test_value_watchp_string():
    await _test_value(
        lambda x:
            rx.watchp(x, 'my_value')
    )
