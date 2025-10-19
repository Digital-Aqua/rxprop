
import unittest
from unittest.mock import Mock
from .notifier import Notifier, ChangeNotifierBase

class TestNotifier(unittest.TestCase):

    def test_bind_and_fire(self):
        notifier = Notifier[int]()
        handler = Mock()
        
        lt = notifier.bind(handler)
        
        notifier.fire(42)
        handler.assert_called_once_with(42)

    def test_unbind(self):
        notifier = Notifier[int]()
        handler = Mock()
        
        lt = notifier.bind(handler)
        lt.dispose()

        notifier.fire(42)
        handler.assert_not_called()

    def test_change_notifier_base(self):
        change_notifier = ChangeNotifierBase()
        handler = Mock()

        lt = change_notifier.on_change.bind(handler)
        change_notifier.on_change.fire(None)

        handler.assert_called_once_with(None)

if __name__ == '__main__':
    unittest.main()
