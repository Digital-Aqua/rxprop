
import unittest
from unittest.mock import Mock
from .reactive_property import ReactivePropertyMixin
from .reactive import DependencyCollection
from .notifier import Notifier

class TestReactiveProperty(unittest.TestCase):

    def test_get_announces_dependency(self):
        
        class MyProperty(ReactivePropertyMixin[object, int]):
            pass

        class MyObject:
            a = MyProperty()

        obj = MyObject()
        obj.a = 42

        handler = Mock()
        collection = DependencyCollection(handler)

        with collection.listen_for_dependencies():
            _ = obj.a
        
        # To test if dependency was announced, we set the value and check if the handler is called
        obj.a = 43
        handler.assert_called_once()


    def test_set_fires_notifier(self):
        class MyProperty(ReactivePropertyMixin[object, int]):
            pass

        class MyObject:
            a = MyProperty()

        obj = MyObject()
        
        notifier = obj.a.get_property()._get_notifier(obj)
        handler = Mock()
        notifier.bind(handler)

        obj.a = 42
        handler.assert_called_once()

    def test_change_notifier_value(self):
        class MyProperty(ReactivePropertyMixin[object, Notifier]):
            pass

        class MyObject:
            a = MyProperty()

        obj = MyObject()
        change_notifier = Notifier[None]()
        obj.a = change_notifier
        
        handler = Mock()
        collection = DependencyCollection(handler)

        with collection.listen_for_dependencies():
            _ = obj.a

        change_notifier.fire(None)
        handler.assert_called_once()


if __name__ == '__main__':
    unittest.main()
