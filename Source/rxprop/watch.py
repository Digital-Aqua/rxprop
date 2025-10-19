from typing import Any, AsyncIterator, overload

from .reactive import watchf
from .reactive_property import ReactivePropertyMixin
from .typed_property import TClass, TValue


@overload
def watchp(
    instance: TClass,
    property: ReactivePropertyMixin[TClass, TValue]
) -> AsyncIterator[TValue]:
    ...

@overload
def watchp(
    instance: object,
    property: str
) -> AsyncIterator[Any]:
    ...

def watchp(
    instance: TClass,
    property: ReactivePropertyMixin[TClass, TValue] | str
) -> AsyncIterator[TValue | Any]:
    """
    Asynchronously watches a reactive property on an instance.

    This function works by tracking which reactive properties are accessed
    during the execution of the property's getter. When any of these
    dependencies change, the property is re-evaluated, and the new result
    is yielded.

    Note:
        This function is NOT guaranteed to yield intermediate values if the
        dependencies change multiple times in quick succession before the
        async event loop processes the changes. It prioritizes yielding the
        latest consistent state.

    Args:
        instance: The object instance on which the property resides.
        property: The property itself (usually on the class,
        e.g. `MyClass.my_value`) or its name (a string).

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
        >>> async for value in watchp(obj, 'my_value'):
        ...     print(f"Value changed to: {value}")
    """

    # Type-strong path
    if not isinstance(property, str):
        return watchf(lambda: property.get(instance))
    
    # Type-weak path
    cls: type = type(instance)
    prop = getattr(cls, property)
    if not isinstance(prop, ReactivePropertyMixin):
        raise ValueError(f"{property} is not a reactive property")
    return watchf(lambda: prop.get(instance)) # type: ignore

