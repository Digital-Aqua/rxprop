
import unittest
from .lifetime import Lifetime

class TestLifetime(unittest.TestCase):

    def test_explicit_dispose(self):
        lt = Lifetime()
        self.assertTrue(lt.is_alive())
        lt.dispose()
        self.assertFalse(lt.is_alive())

    def test_context_dispose(self):
        lt = Lifetime()
        with lt:
            self.assertTrue(lt.is_alive())
        self.assertFalse(lt.is_alive())

    def test_is_alive(self):
        lt = Lifetime()
        self.assertTrue(lt.is_alive())
        lt.dispose()
        self.assertFalse(lt.is_alive())

if __name__ == '__main__':
    unittest.main()
