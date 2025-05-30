from typing import (
    Any, Callable, Generic, Optional, overload, Self, TypeVar
)


_TClass = TypeVar("_TClass")
_TValue = TypeVar("_TValue")

AnyFunction = Callable[..., Any]
Getter = Callable[[_TClass], _TValue]
Setter = Callable[[_TClass, _TValue], None]
Deleter = Callable[[_TClass], None]


class TypedProperty(Generic[_TClass, _TValue]):
    """
    Provides a type-safe property pattern that can be be used similarly to
    the `property` built-in.

    The main difference is that this class is object-oriented rather than
    functional.
    """
    def __init__(self, *, fref: Optional[AnyFunction] = None, **__: Any):
        self.__doc__ = fref.__doc__ if fref else ''
        self._name = fref.__name__ if fref else ''

    @overload
    def __get__(self, instance: None, owner: type[_TClass]) -> Self: ...

    @overload
    def __get__(self, instance: _TClass, owner: type[_TClass]) -> _TValue: ...

    def __get__(self,
        instance: Optional[_TClass],
        owner: type[_TClass]
    ) -> _TValue | Self:
        if instance is None:
            return self
        return self._get(instance)
    
    def get(self, instance: _TClass) -> _TValue:
        """
        Gets the value of the property for the given instance.
        """
        return self._get(instance)

    def _get(self, instance: _TClass) -> _TValue:
        """
        An easily-overridable implementation of `__get__`.
        """
        raise AttributeError(f"Property '{self._name}' does not have a value.")

    def __set__(self, instance: _TClass, value: _TValue) -> None:
        self._set(instance, value)

    def _set(self, instance: _TClass, value: _TValue ) -> None:
        """
        An easily-overridable implementation of `__set__`.
        """
        raise AttributeError(f"Property '{self._name}' does not support setting a value.")

    def __delete__(self, instance: _TClass) -> None:
        self._delete(instance)
        
    def _delete(self, instance: _TClass) -> None:
        """
        An easily-overridable implementation of `__delete__`.
        """
        raise AttributeError(f"Property '{self._name}' does not support deleting a value.")

    def __set_name__(self, owner: type[_TClass], name: str) -> None:
        self._name = name


class GetterMixin(TypedProperty[_TClass, _TValue]):
    """
    Adds a user-customisable `getter` to a `TypedProperty`.
    """
    def __init__(self, *, fget: Optional[Getter[_TClass, _TValue]] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.fget = fget

    def getter(self, fget: Getter[_TClass, _TValue]) -> Self:
        """
        Sets the `getter` function on this property.
        """
        self.fget = fget
        return self

    def _get(self, instance: _TClass) -> _TValue:
        if self.fget is None:
            return super()._get(instance)
        return self.fget(instance)


class SetterMixin(TypedProperty[_TClass, _TValue]):
    """
    Adds a user-customisable `setter` to a `TypedProperty`.
    """
    def __init__(self, *, fset: Optional[Setter[_TClass, _TValue]] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.fset = fset

    def setter(self, fset: Setter[_TClass, _TValue]) -> Self:
        """
        Sets the `setter` function on this property.
        """
        self.fset = fset
        return self

    def _set(self, instance: _TClass, value: _TValue) -> None:
        if self.fset is None:
            return super()._set(instance, value)
        self.fset(instance, value)


class DeleterMixin(TypedProperty[_TClass, _TValue]):
    """
    Adds a user-customisable `deleter` to a `TypedProperty`.
    """
    def __init__(self, *, fdel: Optional[Deleter[_TClass]] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.fdel = fdel

    def deleter(self, fdel: Deleter[_TClass]) -> Self:
        """
        Sets the `deleter` function on this property.
        """
        self.fdel = fdel
        return self

    def _delete(self, instance: _TClass) -> None:
        if self.fdel is None:
            return super()._delete(instance)
        self.fdel(instance)


class DefaultMixin(TypedProperty[_TClass, _TValue]):
    """
    Adds a default value factory to a `TypedProperty`.
    """
    def __init__(self, fdefault: Getter[_TClass, _TValue], **kwargs: Any):
        super().__init__(**kwargs)
        self.fdefault = fdefault

    def _get(self, instance: _TClass) -> _TValue:
        return self.fdefault(instance)

    def default(self, fdefault: Getter[_TClass, _TValue]) -> Self:
        """
        Sets the default value factory for the property.
        """
        self.fdefault = fdefault
        return self

