
import unittest
from .typed_property import TypedProperty, GetterMixin, SetterMixin, DeleterMixin, StrongProperty, prop

class TestTypedProperty(unittest.TestCase):

    def test_typed_property_default_behavior(self):
        class MyObject:
            a = TypedProperty[object, int]()
        
        obj = MyObject()
        with self.assertRaises(AttributeError):
            _ = obj.a
        with self.assertRaises(AttributeError):
            obj.a = 5

    def test_getter_mixin(self):
        class MyProperty(GetterMixin[object, int]):
            pass

        class MyObject:
            a = MyProperty(fget=lambda self: 42)

        obj = MyObject()
        self.assertEqual(obj.a, 42)

    def test_setter_mixin(self):
        class MyProperty(SetterMixin[object, int]):
            pass

        class MyObject:
            _a = 0
            a = MyProperty(fset=lambda self, value: setattr(self, '_a', value))
        
        obj = MyObject()
        obj.a = 42
        self.assertEqual(obj._a, 42)

    def test_deleter_mixin(self):
        class MyProperty(DeleterMixin[object, int]):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._value = 42
            def _get(self, instance) -> int:
                return self._value
            def _set(self, instance, value):
                self._value = value

        class MyObject:
            _a_deleted = False
            def del_a(self):
                self._a_deleted = True

            a = MyProperty(fdel=del_a)

        obj = MyObject()
        self.assertEqual(obj.a, 42)
        del obj.a
        self.assertTrue(obj._a_deleted)

    def test_strong_property(self):
        class MyObject:
            _a = 0
            
            def get_a(self):
                return self._a
            
            def set_a(self, value):
                self._a = value

            a = StrongProperty(fget=get_a, fset=set_a)
            
        obj = MyObject()
        obj.a = 42
        self.assertEqual(obj.a, 42)
        
    def test_prop_decorator(self):
        class MyObject:
            _a = 0

            @prop
            def a(self):
                return self._a
            
            @a.setter
            def a(self, value):
                self._a = value

        obj = MyObject()
        obj.a = 42
        self.assertEqual(obj.a, 42)


if __name__ == '__main__':
    unittest.main()
