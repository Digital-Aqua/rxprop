
import unittest
from unittest.mock import Mock
from .value_property import ValueProperty, ReactiveValueProperty, value, rxvalue

class TestValueProperty(unittest.TestCase):

    def test_value_property_storage(self):
        class MyObject:
            a = ValueProperty(fdefault=lambda self: 42)

        obj = MyObject()
        self.assertEqual(obj.a, 42)
        obj.a = 99
        self.assertEqual(obj.a, 99)

    def test_reactive_value_property_notification(self):
        class MyObject:
            a = ReactiveValueProperty(fdefault=lambda self: 42)

        obj = MyObject()
        
        notifier = obj.a.get_property()._get_notifier(obj)
        handler = Mock()
        notifier.bind(handler)

        obj.a = 99
        handler.assert_called_once()
        
    def test_reactive_value_property_no_notification_on_same_value(self):
        class MyObject:
            a = ReactiveValueProperty(fdefault=lambda self: 42)

        obj = MyObject()
        
        notifier = obj.a.get_property()._get_notifier(obj)
        handler = Mock()
        notifier.bind(handler)

        obj.a = 42
        handler.assert_not_called()
        
    def test_value_decorator(self):
        class MyObject:
            @value
            def a(self):
                return 42
        
        obj = MyObject()
        self.assertEqual(obj.a, 42)
        
    def test_rxvalue_decorator(self):
        class MyObject:
            @rxvalue
            def a(self):
                return 42

        obj = MyObject()
        self.assertEqual(obj.a, 42)

        notifier = obj.a.get_property()._get_notifier(obj)
        handler = Mock()
        notifier.bind(handler)

        obj.a = 99
        handler.assert_called_once()

if __name__ == '__main__':
    unittest.main()
