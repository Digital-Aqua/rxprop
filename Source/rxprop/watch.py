from typing import Any, AsyncIterator, overload, TypeVar

from .reactive import watchf
from .reactive_property import ReactivePropertyMixin


_TClass = TypeVar("_TClass")
_TValue = TypeVar("_TValue")

@overload
def watchp(
    instance: _TClass,
    property: ReactivePropertyMixin[_TClass, _TValue]
) -> AsyncIterator[_TValue]:
    """
    Asynchronously watches a specific reactive property on an instance for
    changes.

    Args:
        instance: The object instance on which the property resides.
        property: The reactive property itself (a `ReactivePropertyMixin`
                  instance).

    Returns:
        An asynchronous iterator (`AsyncIterator`) that yields the property's
        current value and subsequent new values upon change.

    Example:
        >>> class MyClass:
        ...     @rx.value
        ...     def my_value(self) -> int:
        ...         return 1
        ...
        >>> obj = MyClass()
        >>> async for value in watch(obj, MyClass.my_value):
        ...     print(f"Value changed to: {value}")
    """
    ...

@overload
def watchp(
    instance: object,
    property: str
) -> AsyncIterator[Any]:
    """
    Asynchronously watches a reactive property on an instance by its name.

    Args:
        instance: The object instance on which the property resides.
        property: The name of the reactive property (a string).

    Returns:
        An asynchronous iterator (`AsyncIterator[Any]`) that yields the
        property's current value and subsequent new values upon change.

    Example:
        >>> class MyClass:
        ...     @rx.value
        ...     def my_value(self) -> int:
        ...         return 1
        ...
        >>> obj = MyClass()
        >>> async for value in watch(obj, 'my_value'):
        ...     print(f"Value changed to: {value}")
    """
    ...

def watchp(
    instance: _TClass,
    property: ReactivePropertyMixin[_TClass, _TValue] | str
) -> AsyncIterator[_TValue | Any]:
    """
    Asynchronously watches a reactive property for changes and yields new values.

    This function supports two modes of operation based on the `property` argument:
    1.  Direct Property Reference:
        If `property` is an instance of `ReactivePropertyMixin`, the watch
        is set up directly. The async iterator will yield values of the
        specific type `_TValue` associated with the property.
        Example: `async for val in watch(obj, MyClass.some_property): ...`

    2.  Property Name (String):
        If `property` is a string, it's treated as the name of the reactive
        property to be looked up on the `instance`'s class. The async
        iterator will yield values of type `Any`.
        Example: `async for val in watch(obj, "some_property_name"): ...`

    The iterator will first yield the current value of the property upon iteration,
    and subsequently yield new values as the property changes.

    Args:
        instance: The object instance on which the property resides.
        property: The reactive property itself (a `ReactivePropertyMixin`
                  instance) or its name (a string).

    Returns:
        An asynchronous iterator (`AsyncIterator`) that yields the property's
        current value and subsequent new values upon change.

    Raises:
        ValueError: If `property` is a string but does not correspond to a
                    `ReactivePropertyMixin` on the instance's class.
    """
    # Type-strong path
    if not isinstance(property, str):
        return watchf(lambda: property.get(instance))
    
    # Type-weak path
    cls: type = type(instance)
    prop = getattr(cls, property)
    if not isinstance(prop, ReactivePropertyMixin):
        raise ValueError(f"{property} is not a reactive property")
    return prop.watch_async(instance) # type: ignore

