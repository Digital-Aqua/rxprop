
import unittest
import asyncio
from unittest.mock import Mock
from .reactive import DependencyCollection, announce_dependency, watchf
from .notifier import Notifier

class TestReactive(unittest.TestCase):

    def test_dependency_collection(self):
        handler = Mock()
        collection = DependencyCollection(handler)
        notifier = Notifier[None]()

        collection.add_dependency(notifier)
        notifier.fire(None)
        handler.assert_called_once()

        collection.remove_dependency(notifier)
        notifier.fire(None)
        handler.assert_called_once() # Should not be called again

    def test_listen_for_dependencies(self):
        handler = Mock()
        collection = DependencyCollection(handler)
        notifier1 = Notifier[None]()
        notifier2 = Notifier[None]()

        with collection.listen_for_dependencies():
            announce_dependency(notifier1)
        
        notifier1.fire(None)
        handler.assert_called_once()
        
        notifier2.fire(None)
        handler.assert_called_once()

    def test_watchf(self):
        
        class MyObject:
            def __init__(self):
                self._a = 1
                self.on_a_change = Notifier[None]()
            
            @property
            def a(self):
                announce_dependency(self.on_a_change)
                return self._a
            
            @a.setter
            def a(self, value):
                self._a = value
                self.on_a_change.fire(None)

        obj = MyObject()

        async def test_async():
            results = []
            async for value in watchf(lambda: obj.a):
                results.append(value)
                if len(results) == 2:
                    break
                # In a real application, the event loop would be running.
                # Here we manually trigger the change.
                asyncio.create_task(self.change_value(obj))

            self.assertEqual(results, [1, 2])
        
        asyncio.run(test_async())

    async def change_value(self, obj):
        await asyncio.sleep(0.01) # allow the watcher to suspend
        obj.a = 2

if __name__ == '__main__':
    unittest.main()
