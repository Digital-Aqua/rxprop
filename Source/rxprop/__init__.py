"""
Super-simple reactive properties.
"""
__version__ = "0.1.0"

from .value_property import value
from .computed_property import computed
from .reactive import watchf
from .watch_property import watchp
from .notifier import Notifier

__all__ = [
    "value",
    "computed",
    "watchf",
    "watchp",
    "Notifier",
]
