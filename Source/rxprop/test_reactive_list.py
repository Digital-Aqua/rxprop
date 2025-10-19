
import unittest
from unittest.mock import Mock
from .reactive_list import ReactiveList

class TestReactiveList(unittest.TestCase):

    def setUp(self):
        self.list = ReactiveList([1, 2, 3])
        self.handler = Mock()
        self.list.on_change.bind(self.handler)

    def test_setitem(self):
        self.list[0] = 4
        self.assertEqual(self.list[0], 4)
        self.handler.assert_called_once()

    def test_delitem(self):
        del self.list[0]
        self.assertEqual(len(self.list), 2)
        self.handler.assert_called_once()

    def test_insert(self):
        self.list.insert(0, 4)
        self.assertEqual(self.list[0], 4)
        self.handler.assert_called_once()
        
    def test_append(self):
        self.list.append(4)
        self.assertEqual(self.list[-1], 4)
        self.handler.assert_called_once()
        
    def test_clear(self):
        self.list.clear()
        self.assertEqual(len(self.list), 0)
        self.handler.assert_called_once()
        
    def test_extend(self):
        self.list.extend([4, 5])
        self.assertEqual(len(self.list), 5)
        self.handler.assert_called_once()
        
    def test_pop(self):
        self.list.pop()
        self.assertEqual(len(self.list), 2)
        self.handler.assert_called_once()
        
    def test_remove(self):
        self.list.remove(2)
        self.assertNotIn(2, self.list)
        self.handler.assert_called_once()
        
    def test_reverse(self):
        self.list.reverse()
        self.assertEqual(self.list[0], 3)
        self.handler.assert_called_once()

if __name__ == '__main__':
    unittest.main()
