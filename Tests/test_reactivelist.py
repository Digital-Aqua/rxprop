from asyncio import create_task
from typing import AsyncIterator, Callable, Sequence

import pytest

import rxprop as rx

from utils import flush_event_loop


def test_reactivelist():

    obj = rx.ReactiveList[int]()

    received_values: list[list[int]] = []
    def handler(_: None):
        received_values.append(list(obj))
    
    assert isinstance(obj, rx.PChangeNotifier)
    assert list(obj) == []

    with obj.on_change.bind(handler):
        obj.append(1)
        obj.append(2)
        obj.append(3)
        obj.append(3)
        obj.pop()
        obj.pop(1)
        obj.insert(0, 0)
        obj.remove(3)
        obj.clear()
        obj.extend([4, 5, 6])
        obj.reverse()

    obj.append(4)

    assert list(obj) == [6, 5, 4, 4]
    assert obj.index(6) == 0
    assert obj.count(6) == 1
    assert 6 in obj
    assert 7 not in obj
    assert len(obj) == 4
    assert obj[0] == 6
    assert obj[1] == 5
    assert obj[2] == 4
    assert obj[0:2] == [6, 5]
    assert obj[0:2:2] == [6]
    assert obj[::-1] == [4, 4, 5, 6]
    
    assert received_values == [
        [1],
        [1, 2],
        [1, 2, 3],
        [1, 2, 3, 3],
        [1, 2, 3],
        [1, 3],
        [0, 1, 3],
        [0, 1],
        [],
        [4, 5, 6],  
        [6, 5, 4],
    ]


class ValueListExample:
    @rx.value
    def my_list(self) -> rx.ReactiveList[int]:
        return rx.ReactiveList[int]()

    @rx.computed
    def my_list_length(self) -> int:
        return len(self.my_list)

    @rx.computed
    def my_list_doubled(self) -> Sequence[int]:
        return [ x * 2 for x in self.my_list ]


async def _test_value_list(
    watch_factory: Callable[[ValueListExample], AsyncIterator[rx.ReactiveList[int]]]
):
    model = ValueListExample()
    received_values: list[list[int]] = []

    # Watch
    async def watch_value():
        nonlocal received_values
        async for value in watch_factory(model):
            print(f"Received value: {value}")
            received_values.append(list(value))
            if len(received_values) >= 4:
                break
    task = create_task(watch_value())
    
    # Check initial value
    assert list(model.my_list) == []
    await flush_event_loop()
    assert received_values == [[]]

    # Check append
    model.my_list.append(1)
    assert list(model.my_list) == [1]
    await flush_event_loop()
    assert received_values == [[], [1]]

    # Check another append
    model.my_list.append(2)
    assert list(model.my_list) == [1, 2]
    await flush_event_loop()
    assert received_values == [[], [1], [1, 2]]

    # Check remove
    model.my_list.remove(1)
    assert list(model.my_list) == [2]
    await flush_event_loop()
    assert received_values == [[], [1], [1, 2], [2]]

    # Verify processing
    await flush_event_loop()
    assert task.done()
    assert not task.exception()

@pytest.mark.asyncio
async def test_value_list_watchf():
    await _test_value_list(
        lambda x: rx.watchf(lambda: x.my_list)
    )

@pytest.mark.asyncio
async def test_value_list_watchp_property():
    await _test_value_list(
        lambda x: rx.watchp(x, ValueListExample.my_list)
    )

@pytest.mark.asyncio
async def test_value_list_watchp_string():
    await _test_value_list(
        lambda x: rx.watchp(x, 'my_list')
    )


async def _test_computed_list(
    watch_factory: tuple[
        Callable[[ValueListExample], AsyncIterator[rx.ReactiveList[int]]],
        Callable[[ValueListExample], AsyncIterator[int]],
        Callable[[ValueListExample], AsyncIterator[Sequence[int]]]
    ]
):
    model = ValueListExample()
    received_values: list[list[int]] = []
    received_length: list[int] = []
    received_doubled: list[list[int]] = []

    # Watch
    async def watch_value():
        nonlocal received_values
        async for value in watch_factory[0](model):
            print(f"Received value: {value}")
            received_values.append(list(value))
            if len(received_values) >= 4:
                break
    task = create_task(watch_value())
    
    async def watch_length():
        nonlocal received_length
        async for value in watch_factory[1](model):
            print(f"Received length: {value}")
            received_length.append(value)
            if len(received_length) >= 4:
                break
    task_length = create_task(watch_length())

    async def watch_doubled():
        nonlocal received_doubled
        async for value in watch_factory[2](model):
            print(f"Received doubled: {value}")
            received_doubled.append(list(value))
            if len(received_doubled) >= 4:
                break
    task_doubled = create_task(watch_doubled())

    # Check initial value
    assert list(model.my_list) == []
    assert model.my_list_length == 0
    assert list(model.my_list_doubled) == []
    await flush_event_loop()
    assert received_values == [[]]
    assert received_length == [0]
    assert received_doubled == [[]]

    # Check append
    model.my_list.append(1)
    assert list(model.my_list) == [1]
    assert model.my_list_length == 1
    assert list(model.my_list_doubled) == [2]
    await flush_event_loop()
    assert received_values == [[], [1]]
    assert received_length == [0, 1]
    assert received_doubled == [[], [2]]

    # Check another append
    model.my_list.append(2)
    assert list(model.my_list) == [1, 2]
    assert model.my_list_length == 2
    assert list(model.my_list_doubled) == [2, 4]
    await flush_event_loop()
    assert received_values == [[], [1], [1, 2]]
    assert received_length == [0, 1, 2]
    assert received_doubled == [[], [2], [2, 4]]

    # Check remove
    model.my_list.remove(1)
    assert list(model.my_list) == [2]
    assert model.my_list_length == 1
    assert list(model.my_list_doubled) == [4]
    await flush_event_loop()
    assert received_values == [[], [1], [1, 2], [2]]
    assert received_length == [0, 1, 2, 1]
    assert received_doubled == [[], [2], [2, 4], [4]]
    
    # Verify processing
    await flush_event_loop()
    assert task.done()
    assert not task.exception()
    assert task_length.done()
    assert not task_length.exception()
    assert task_doubled.done()
    assert not task_doubled.exception()

@pytest.mark.asyncio
async def test_computed_list_watchf():
    await _test_computed_list(
        (
            lambda x: rx.watchf(lambda: x.my_list),
            lambda x: rx.watchf(lambda: x.my_list_length),
            lambda x: rx.watchf(lambda: x.my_list_doubled),
        )
    )

@pytest.mark.asyncio
async def test_computed_list_watchp_property():
    await _test_computed_list(
        (
            lambda x: rx.watchp(x, ValueListExample.my_list),
            lambda x: rx.watchp(x, ValueListExample.my_list_length),
            lambda x: rx.watchp(x, ValueListExample.my_list_doubled),
        )
    )

@pytest.mark.asyncio
async def test_computed_list_watchp_string():
    await _test_computed_list(
        (
            lambda x: rx.watchp(x, 'my_list'),
            lambda x: rx.watchp(x, 'my_list_length'),
            lambda x: rx.watchp(x, 'my_list_doubled'),
        )
    )
