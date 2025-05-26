from types import TracebackType
from weakref import finalize


class Disposable:
    """
    Base class for disposable objects.
    Exposes automatic disposal via finalization (GC),
    and explicit disposal via `dispose()`.
    """
    def __init__(self):
        self._is_disposed = False
        finalize(self, self._dispose)
    
    def dispose(self):
        """ Explicitly disposes of this Lifetime object. """
        self._dispose()

    def _dispose(self):
        """ Disposal logic. """
        self._is_disposed = True


class Lifetime(Disposable):
    """
    Represents a lifetime.
    Exposes automatic disposal via finalization (GC),
    context disposal via `with` blocks,
    and explicit disposal via `dispose()`.
    """
    def __enter__(self):
        return self

    def __exit__(self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None
    ) -> bool:
        self._dispose()
        return False

    def is_alive(self) -> bool:
        """ Returns True if this lifetime is still alive. """
        return not self._is_disposed

