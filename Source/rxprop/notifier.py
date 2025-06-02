from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable
from weakref import WeakSet, ref as weak_ref

from .lifetime import Lifetime


_TArgs = TypeVar('_TArgs')
_THandler = Callable[[_TArgs], None]


class Notifier(Generic[_TArgs]):
    """
    A source of notification events.
    """
    def __init__(self):
        self._bindings = WeakSet['Notifier[_TArgs]._BindingLifetime']()

    class _BindingLifetime(Lifetime):
        """
        A container for a binding between a notifier and a handler.
        Keeps the handler alive; does not keep the notifier alive.
        """
        def __init__(self,
            notifier: 'Notifier[_TArgs]',
            handler: _THandler[_TArgs]
        ):
            self._notifier = weak_ref(notifier)
            self.handler = handler
            notifier._bindings.add(self)

        def unbind(self):
            """
            Unbinds this binding from its notifier.
            This is called automatically when the lifetime object is disposed.
            Robust to multiple calls.
            """
            if self._notifier and (notifier := self._notifier()):
                notifier._bindings.remove(self)
            self._notifier = None
            self.handler = None

        def _dispose(self):
            self.unbind()
            super()._dispose()

    def bind(self, handler: _THandler[_TArgs]) -> 'Lifetime':
        """
        Binds a handler to this notifier.
        Returns a lifetime object that keeps the binding alive.
        Release the lifetime object to unbind the handler;
        either explicitly via a `with` block,
        or just by letting the lifetime go out of scope.
        This notifier will NOT keep the binding alive;
        but the lifetime object WILL keep the handler alive.
        """
        return self._BindingLifetime(self, handler)

    def fire(self, args: _TArgs) -> None:
        """
        Fires all handlers bound to this notifier.
        """
        # Fire handlers carefully,
        # in case one of them messes with self._bindings
        for binding in list(self._bindings):
            if binding in self._bindings and binding.handler:
                binding.handler(args)


@runtime_checkable
class PChangeNotifier(Protocol):
    """
    Protocol for manual change notification.
    """
    @property
    def on_change(self) -> Notifier[None]:
        ...


class ChangeNotifierBase(PChangeNotifier):
    """
    Base implementation of manual change notification via an
    `on_change: Notifier[None]` property.
    """
    def __init__(self):
        self._on_change = Notifier[None]()

    @property
    def on_change(self) -> Notifier[None]:
        return self._on_change
