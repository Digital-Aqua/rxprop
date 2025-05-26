from asyncio import Event, sleep
from contextlib import contextmanager
from typing import AsyncIterator, Callable, Iterator, TypeVar
from weakref import WeakKeyDictionary

from .notifier import Notifier
from .lifetime import Lifetime


_SimpleNotifier = Notifier[None]
_SimpleHandler = Callable[[None], None]
_TValue = TypeVar("_TValue")

_dep_ctx_stack: list[set[_SimpleNotifier]] = []


class DependencyCollection(Lifetime):
    """
    Manages a collection of dependencies.
    """
    def __init__(self, handler: _SimpleHandler):
        super().__init__()
        self._bindings = WeakKeyDictionary[_SimpleNotifier, Lifetime]()
        self._handler: _SimpleHandler|None = handler

    def add_dependency(self, notifier: _SimpleNotifier):
        """ Adds a dependency to this collection. """
        assert self.is_alive()
        if notifier in self._bindings: return
        if not self._handler: return
        binding = notifier.bind(self._handler)
        self._bindings[notifier] = binding

    def remove_dependency(self, notifier: _SimpleNotifier):
        """ Removes a dependency from this collection. """
        assert self.is_alive()
        self._bindings.pop(notifier)

    @contextmanager
    def listen_for_dependencies(self) -> Iterator[None]:
        """
        Listens for dependencies in a context,
        and updates this collection accordingly.
        """
        assert self.is_alive()
        buffer = set[_SimpleNotifier]()
        _dep_ctx_stack.append(buffer)
        try:
            yield
        finally:
            bindings = set(self._bindings.keys())
            _dep_ctx_stack.pop()
            for dep in buffer - bindings:
                self.add_dependency(dep)
            for dep in bindings - buffer:
                self.remove_dependency(dep)

    def _dispose(self):
        self._bindings.clear()
        self._handler = None
        super()._dispose()


@contextmanager
def dependency_collection(handler: _SimpleHandler) -> Iterator[DependencyCollection]:
    """
    Context manager that creates a new dependency collection.
    """
    deps = DependencyCollection(handler)
    try:
        yield deps
    finally:
        assert deps # Keep alive


def announce_dependency(
    notifier: _SimpleNotifier|Callable[[], _SimpleNotifier]
):
    """
    Announces a dependency to anyone listening.
    """
    if _dep_ctx_stack:
        if callable(notifier):
            notifier = notifier()
        _dep_ctx_stack[-1].add(notifier)


async def watchf(
    f: Callable[[], _TValue]
) -> AsyncIterator[_TValue]:
    """
    Asynchronously observes the result of a function and yields new values
    whenever any reactive properties accessed within that function change.

    This function works by tracking which reactive properties are accessed
    during the execution of the provided callable `f`. When any of these
    dependencies change, `f` is re-evaluated, and the new result is yielded.

    The iterator will first yield the initial result of `f()` upon iteration.
    Subsequently, it will yield new results as the underlying reactive
    dependencies of `f` change.

    Note:
        This function is NOT guaranteed to yield intermediate values if the
        dependencies change multiple times in quick succession before the
        async event loop processes the changes. It prioritizes yielding the
        latest consistent state.

    Args:
        f: A callable that takes no arguments and returns a value of type `_TValue`.
           This function will be re-executed when its reactive dependencies change.

    Returns:
        An asynchronous iterator (`AsyncIterator[_TValue]`) that yields the
        initial result of `f()` and subsequent new results upon change.

    Example:
        >>> class MyClass:
        ...     @rx.value
        ...     def my_value(self) -> int:
        ...         return 1
        ...
        >>> obj = MyClass()
        >>> async for value in watchf(lambda: obj.my_value):
        ...     print(f"Value changed to: {value}")

    """
    changed = Event() # An event that is set when a dependency changes
    with dependency_collection(lambda _: changed.set()) as deps:
        while True:
            # Get value (listening for dependencies)
            with deps.listen_for_dependencies():
                value = f()
            yield value
            await changed.wait()
            await sleep(0)
            changed.clear()
