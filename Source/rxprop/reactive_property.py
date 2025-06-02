from typing import Any, Callable
from weakref import WeakKeyDictionary

from .reactive import announce_dependency
from .notifier import Notifier, PChangeNotifier
from .typed_property import TypedProperty, TypeVar


_SimpleNotifier = Notifier[None]
_SimpleHandler = Callable[[None], None]
_TClass = TypeVar("_TClass")
_TValue = TypeVar("_TValue")


class ReactivePropertyMixin(TypedProperty[_TClass, _TValue]):
    """
    A mixin for reactive properties.
    Reports usage of the property to dependency tracking,
    and provides methods to assist .
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

    def _get(self, instance: _TClass) -> _TValue:
        announce_dependency(self._get_notifier(instance))
        value = super()._get(instance)
        if isinstance(value, PChangeNotifier):
            announce_dependency(value.on_change)
        return value

    def _set(self, instance: _TClass, value: _TValue) -> None:
        super()._set(instance, value)
        self._fire_notifier(instance)
