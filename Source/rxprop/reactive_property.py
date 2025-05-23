import asyncio
from contextlib import contextmanager
from typing import Any, AsyncIterator, Callable, Iterator
from weakref import WeakKeyDictionary

from .notifier import Notifier
from .typed_property import (
    Getter, GetterMixin, SetterMixin, TypedProperty, TypeVar
)


_SimpleNotifier = Notifier[None]
_SimpleHandler = Callable[[None], None]
_TClass = TypeVar("_TClass")
_TValue = TypeVar("_TValue")


_dep_ctx_stack: list[set[_SimpleNotifier]] = []


@contextmanager
def listen_for_dependencies(
    buffer: set[_SimpleNotifier],
    handler: _SimpleHandler|None = None
) -> Iterator[None]:
    """
    Context manager that listens for dependencies and adds them to `buffer`.
    If `handler` is provided, it will be added to any new dependencies and
    removed from any old dependencies.
    Temporarily suppresses existing listeners until the context manager exits.
    """
    new_deps = set[_SimpleNotifier]()
    _dep_ctx_stack.append(new_deps)
    try:
        yield
    finally:
        _dep_ctx_stack.pop()
        for dep in new_deps - buffer:
            buffer.add(dep)
            if handler is not None:
                dep.add_handler(handler)
        for dep in buffer - new_deps:
            buffer.discard(dep)
            if handler is not None:
                dep.remove_handler(handler)


async def watch_function(
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

    Example:
        Consider a class `MyData` with reactive properties `a` and `b`.
        ```python
        class MyData:
            a = ReactiveProperty(initial_value=1)
            b = ReactiveProperty(initial_value=2)

        data = MyData()

        async def sum_watcher():
            # watch_function will track that data.a and data.b are dependencies
            async for total in watch_function(lambda: data.a + data.b):
                print(f"Sum is now: {total}")

        # In an async context:
        # await sum_watcher()
        #
        # Output:
        # Sum is now: 3
        #
        # If data.a is changed to 10:
        # data.a = 10
        # Output:
        # Sum is now: 12
        ```

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
        initial result of `f()` and subsequent new results upon changes to
        its reactive dependencies.
    """
    changed = asyncio.Event() # An event that is set when a dependency changes
    deps = set[_SimpleNotifier]() # Our set of dependencies (notifiers)
    setter: _SimpleHandler = lambda _: changed.set() # A handler that sets the event

    try:
        while True:
            # Get value (listening for dependencies)
            with listen_for_dependencies(deps, setter):
                value = f()
            yield value
            await changed.wait()
            await asyncio.sleep(0)
            changed.clear()

    finally:
        for dep in deps:
            dep.remove_handler(setter)


class ReactivePropertyMixin(TypedProperty[_TClass, _TValue]):
    """
    A mixin for reactive properties.
    Provides `observe_async` for change notification,
    and reports usage of the property to dependency tracking.
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._notifiers = WeakKeyDictionary[_TClass, _SimpleNotifier]()
        self._triggers = WeakKeyDictionary[_TClass, _SimpleHandler]()

    def _get_notifier(self, instance: _TClass) -> _SimpleNotifier:
        """
        Returns a notifier for the given instance.
        If the notifier is not in the stash, a new notifier is created
        and added to the stash.
        """
        if not instance in self._notifiers:
            self._notifiers[instance] = _SimpleNotifier()
        return self._notifiers[instance]

    def _get_notifier_trigger(self, instance: _TClass) -> _SimpleHandler:
        """
        Returns `_fire_notifier` as a handler.
        """
        if not instance in self._triggers:
            self._triggers[instance] = lambda _: self._fire_notifier(instance)
        return self._triggers[instance]

    def _fire_notifier(self, instance: _TClass) -> None:
        """
        Fires the notifier for the given instance.
        """
        notifier = self._get_notifier(instance)
        notifier.fire(None)

    def _announce_dependency(self, instance: _TClass) -> None:
        """
        Announce a dependency to anyone who's listening.
        """
        if _dep_ctx_stack:
            notifier = self._get_notifier(instance)
            _dep_ctx_stack[-1].add(notifier)

    def _get(self, instance: _TClass) -> _TValue:
        self._announce_dependency(instance)
        return super()._get(instance)

    def _set(self, instance: _TClass, value: _TValue) -> None:
        super()._set(instance, value)
        self._fire_notifier(instance)

    async def watch_async(self, instance: _TClass) -> AsyncIterator[_TValue]:
        """
        Observes this property and yields new values when the property changes.

        NOT guaranteed to yield intermediate values if the property changes
        multiple times in quick succession.
        """
        async for value in watch_function(lambda: self._get(instance)):
            yield value


class ReactiveProperty(
    ReactivePropertyMixin[_TClass, _TValue],
    GetterMixin[_TClass, _TValue],
    SetterMixin[_TClass, _TValue]
):
    """
    A reactive property backed by a getter and setter.
    """


def reactive_property(
    fget: Getter[_TClass, _TValue]
) -> ReactiveProperty[_TClass, _TValue]:
    """
    Decorator that creates a reactive property backed by a getter function.
    Allows defining a setter using `@name.setter`.
    """
    # Ensure fref is passed for docstring and name, fget for the actual getter.
    return ReactiveProperty(fget=fget, fref=fget)
