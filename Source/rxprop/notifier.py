import asyncio
from contextlib import contextmanager
from typing import Callable, Generic, Iterator, TypeVar
# from weakref import WeakKeyDictionary # No longer used


_TArgs = TypeVar('_TArgs')
_THandler = Callable[[_TArgs], None]


class Notifier(Generic[_TArgs]):
    """
    A source of notification events.
    """
    def __init__(self):
        # self._handlers = WeakKeyDictionary[Action, int]()
        self._handlers: dict[_THandler[_TArgs], int] = dict()

    @contextmanager
    def handler_context(self, handler: _THandler[_TArgs]) -> Iterator[None]:
        self.add_handler(handler)
        try:
            yield
        finally:
            self.remove_handler(handler)

    @contextmanager
    def event_context(self) -> Iterator[asyncio.Event]:
        """
        Provides an `asyncio.Event` that is set when this notifier is fired.
        """
        event = asyncio.Event()
        with self.handler_context(lambda _: event.set()):
            yield event

    def add_handler(self, handler: _THandler[_TArgs]) -> None:
        self._handlers.setdefault(handler, 0)
        self._handlers[handler] += 1

    def remove_handler(self, handler: _THandler[_TArgs]) -> None:
        self._handlers[handler] -= 1
        if self._handlers[handler] == 0:
            del self._handlers[handler]

    def fire(self, args: _TArgs) -> None:
        # Fire handlers carefully, in case one of them messes with this list
        for handler in list(self._handlers.keys()):
            if handler in self._handlers:
                handler(args)
