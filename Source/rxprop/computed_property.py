from typing import Any, TypeVar
from weakref import WeakKeyDictionary

from .reactive_property import ReactivePropertyMixin
from .typed_property import Getter, GetterMixin

from .reactive import announce_dependency, DependencyCollection


_TClass = TypeVar("_TClass")
_TValue = TypeVar("_TValue")


class CachedPropertyMixin(ReactivePropertyMixin[_TClass, _TValue]):
    """
    A reactive property with a cache and a dirty indicator.
    Prevents re-computation if the property is not dirty (very important!)
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._cache_values = WeakKeyDictionary[_TClass, _TValue]()

    def _fire_notifier(self, instance: _TClass) -> None:
        # Hooks into the change notification pipeline,
        # clearing the cache first, before firing the notifier.
        if instance in self._cache_values:
            del self._cache_values[instance]
        super()._fire_notifier(instance)

    def _get(self,
        instance: _TClass
    ) -> _TValue:
        # Prefer cache; but announce dependency manually,
        # since we're bypassing ReactivePropertyMixin._get(...)
        if instance in self._cache_values:
            notifier = self._get_notifier(instance)
            announce_dependency(notifier)
            return self._cache_values[instance]
        # Recompute, cache, return.
        value = super()._get(instance)
        self._cache_values[instance] = value
        return value

    def _set(self,
        instance: _TClass,
        value: _TValue
    ) -> None:
        # Bypass quickly if possible.
        if instance in self._cache_values:
            if self._cache_values[instance] == value:
                return
        # Update the cache
        self._cache_values[instance] = value
        # Manually fire the notifier,
        # since we're bypassing ReactivePropertyMixin._set(...).
        self._fire_notifier(instance)


class ComputedValueMixin(
    ReactivePropertyMixin[_TClass, _TValue],
    GetterMixin[_TClass, _TValue]
):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._computed_dependencies = \
            WeakKeyDictionary[_TClass, DependencyCollection]()

    def _get_computed_dependencies(self,
        instance: _TClass
    ) -> DependencyCollection:
        if instance not in self._computed_dependencies:
            # Have the dependency collection fire our change notifier
            trigger = self._get_notifier_trigger(instance)
            self._computed_dependencies[instance] = \
                DependencyCollection(trigger)
            # ALSO have the dependency collection clear our cache
        return self._computed_dependencies[instance]

    def _get(self,
        instance: _TClass
    ) -> _TValue:
        deps = self._get_computed_dependencies(instance)
        with deps.listen_for_dependencies():
            # Call the getter more directly, so we don't just get our ourself
            # as a dependency.
            value = GetterMixin[_TClass, _TValue]._get(self, instance)
        return value


class ComputedProperty(
    # Ultimately just a cache backed by a getter.
    # The cache invalidates reactively; the getter provides the computation.
    CachedPropertyMixin[_TClass, _TValue],
    ComputedValueMixin[_TClass, _TValue],
    GetterMixin[_TClass, _TValue]
):
    """
    A reactive property backed by a compute function.
    """


def computed(
    fcompute: Getter[_TClass, _TValue]
) -> ComputedProperty[_TClass, _TValue]:
    """
    Decorator that creates a reactive property backed by a compute function.

    ReactiveProperties that are called within the compute function are
    automatically added as dependencies, triggering notification
    (and typically re-computation) when they change.
    """
    return ComputedProperty(fget=fcompute, fref=fcompute)
