from typing import Any, Callable
from weakref import WeakKeyDictionary

from .reactive import announce_dependency
from .notifier import Notifier, PChangeNotifier
from .typed_property import Getter, TypedProperty, TClass, TValue


_SimpleNotifier = Notifier[None]
_SimpleHandler = Callable[[None], None]


class ReactivePropertyMixin(TypedProperty[TClass, TValue]):
    """
    A mixin for reactive properties.
    Reports usage of the property to dependency tracking,
    and provides methods to assist .
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._notifiers = WeakKeyDictionary[TClass, _SimpleNotifier]()
        self._triggers = WeakKeyDictionary[TClass, _SimpleHandler]()

    def _get_notifier(self, instance: Any) -> _SimpleNotifier:
        """
        Returns a notifier for the given instance.
        If the notifier is not in the stash, a new notifier is created
        and added to the stash.
        """
        if not instance in self._notifiers:
            self._notifiers[instance] = _SimpleNotifier()
        return self._notifiers[instance]

    def _get_notifier_trigger(self, instance: Any) -> _SimpleHandler:
        """
        Returns `_fire_notifier` as a handler.
        """
        if not instance in self._triggers:
            self._triggers[instance] = lambda _: self._fire_notifier(instance)
        return self._triggers[instance]

    def _fire_notifier(self, instance: Any) -> None:
        """
        Fires the notifier for the given instance.
        """
        notifier = self._get_notifier(instance)
        notifier.fire(None)

    def _get(self, instance: Any) -> TValue:
        announce_dependency(self._get_notifier(instance))
        value = super()._get(instance)
        if isinstance(value, PChangeNotifier):
            announce_dependency(value.on_change)
        return value

    def _set(self, instance: Any, value: TValue) -> None:
        super()._set(instance, value)
        self._fire_notifier(instance)


def reactive(
    f: Getter[TClass, TValue]
) -> ReactivePropertyMixin[TClass, TValue]:
    """
    Decorator that indicates a reactive property.

    Provides no functionality.
    Typically used for type hinting, where an abstract property may be
    implemented as either `value` or `computed`.
    """
    return ReactivePropertyMixin(fref=f)
