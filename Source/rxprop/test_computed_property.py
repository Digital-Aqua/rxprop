
import unittest
from unittest.mock import Mock
from .reactive_property import rxproperty
from .computed_property import rxcomputed

class TestComputedProperty(unittest.TestCase):

    def test_basic_computation(self):
        class MyObject:
            def __init__(self):
                self.a = rxproperty(1)

            @rxcomputed
            def b(self) -> int:
                return self.a.get() + 1

        obj = MyObject()
        self.assertEqual(obj.b, 2)

    def test_caching(self):
        class MyObject:
            def __init__(self):
                self.a = rxproperty(1)
                self.b_compute_count = Mock()

            @rxcomputed
            def b(self) -> int:
                self.b_compute_count()
                return self.a.get() + 1

        obj = MyObject()
        self.assertEqual(obj.b, 2)
        self.assertEqual(obj.b, 2)
        self.assertEqual(obj.b_compute_count.call_count, 1)

    def test_recomputation(self):
        class MyObject:
            def __init__(self):
                self.a = rxproperty(1)
                self.b_compute_count = Mock()

            @rxcomputed
            def b(self) -> int:
                self.b_compute_count()
                return self.a.get() + 1

        obj = MyObject()
        self.assertEqual(obj.b, 2)
        self.assertEqual(obj.b_compute_count.call_count, 1)

        obj.a.set(5)
        self.assertEqual(obj.b, 6)
        self.assertEqual(obj.b_compute_count.call_count, 2)

    def test_property_chain(self):
        class MyObject:
            def __init__(self):
                self.a = rxproperty(1)

            @rxcomputed
            def b(self) -> int:
                return self.a.get() + 1
            
            @rxcomputed
            def c(self) -> int:
                return self.b * 2

        obj = MyObject()
        self.assertEqual(obj.c, 4)

        obj.a.set(2)
        self.assertEqual(obj.c, 6)

if __name__ == '__main__':
    unittest.main()
