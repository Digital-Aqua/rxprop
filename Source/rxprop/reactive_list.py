from typing import MutableSequence, TypeVar, overload, Iterable

from .notifier import Notifier, PChangeNotifier


_TValue = TypeVar("_TValue")


class ReactiveList(MutableSequence[_TValue], PChangeNotifier):
    """
    Reactive wrapper for a list, which notifies when the list is changed
    via the `on_change` property.
    """
    def __init__(self, values: Iterable[_TValue] | None = None):
        self._notifier = Notifier[None]()
        self._values: list[_TValue] = list(values or [])

    @property
    def on_change(self) -> Notifier[None]:
        return self._notifier

    @overload
    def __getitem__(self, index: int) -> _TValue:
        ...

    @overload
    def __getitem__(self, index: slice) -> list[_TValue]: # Or ReactiveList[_TValue]
        ...

    def __getitem__(self, index: int | slice) -> _TValue | list[_TValue]:
        if isinstance(index, int):
            return self._values[index]
        return self._values[index]

    @overload
    def __setitem__(self, index: int, value: _TValue) -> None:
        ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[_TValue]) -> None:
        ...

    def __setitem__(self, index: int | slice, value: _TValue | Iterable[_TValue]) -> None:
        if isinstance(index, int):
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                 raise TypeError("Assigning an iterable to a single index is not supported directly without type casting or specific logic.")
            self._values[index] = value # type: ignore
        else: # index is a slice
            if not isinstance(value, Iterable):
                raise TypeError("Can only assign an iterable to a slice.")
            self._values[index] = value # type: ignore
        self._notifier.fire(None)

    @overload
    def __delitem__(self, index: int) -> None:
        ...

    @overload
    def __delitem__(self, index: slice) -> None:
        ...

    def __delitem__(self, index: int | slice) -> None:
        del self._values[index]
        self._notifier.fire(None)

    def __len__(self) -> int:
        return len(self._values)

    def insert(self, index: int, value: _TValue) -> None:
        self._values.insert(index, value)
        self._notifier.fire(None)

    def append(self, value: _TValue) -> None:
        self._values.append(value)
        self._notifier.fire(None)

    def clear(self) -> None:
        self._values.clear()
        self._notifier.fire(None)

    def extend(self, values: Iterable[_TValue]) -> None:
        self._values.extend(values)
        self._notifier.fire(None)

    def pop(self, index: int = -1) -> _TValue:
        value = self._values.pop(index)
        self._notifier.fire(None)
        return value

    def remove(self, value: _TValue) -> None:
        self._values.remove(value)
        self._notifier.fire(None)

    def reverse(self) -> None:
        self._values.reverse()
        self._notifier.fire(None)

    def __str__(self) -> str:
        return str(self._values)

    def __repr__(self) -> str:
        return repr(self._values)
    
