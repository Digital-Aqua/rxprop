from typing import Any
from weakref import WeakKeyDictionary

from .reactive_property import ReactivePropertyMixin
from .typed_property import DefaultMixin, Getter, TClass, TValue, TypedProperty


class ValueProperty(
    DefaultMixin[TClass, TValue],
    TypedProperty[TClass, TValue],
):
    """
    Adds a stash of values to a `TypedProperty`.
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._values = WeakKeyDictionary[TClass, TValue]()

    def _get(self, instance: Any) -> TValue:
        if instance in self._values:
            return self._values[instance]
        value = super()._get(instance)
        self._values[instance] = value
        return value
    
    def _set(self, instance: Any, value: TValue) -> None:
        self._values[instance] = value


class ReactiveValueProperty(
    ReactivePropertyMixin[TClass, TValue], # reactive logic
    ValueProperty[TClass, TValue],         # value storage logic
):
    """
    A reactive property backed by a field.
    """
    def _set(self, instance: Any, value: TValue) -> None:
        # Skip updates (and thus notifications) if the value is the same
        old_value = self._get(instance)
        if old_value != value:
            super()._set(instance, value) # triggers notifier


def value(fdefault: Getter[TClass, TValue]) -> ValueProperty[TClass, TValue]:
    """
    Decorator that creates a non-reactive property backed by a field.
    The decorated function is called (lazily) to generate the default value.
    """
    return ValueProperty(fdefault=fdefault, fref=fdefault)


def rxvalue(fdefault: Getter[TClass, TValue]) -> ReactiveValueProperty[TClass, TValue]:
    """
    Decorator that creates a reactive property backed by a field.
    The decorated function is called (lazily) to generate the default value.
    """
    return ReactiveValueProperty(fdefault=fdefault, fref=fdefault)
