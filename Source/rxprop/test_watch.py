
import unittest
import asyncio
from .watch import watchp
from .value_property import rxvalue

class TestWatch(unittest.TestCase):

    def test_watchp_by_reference(self):
        class MyObject:
            @rxvalue
            def a(self):
                return 1

        obj = MyObject()

        async def test_async():
            results = []
            async for value in watchp(obj, MyObject.a):
                results.append(value)
                if len(results) == 2:
                    break
                asyncio.create_task(self.change_value(obj))
            self.assertEqual(results, [1, 2])
        
        asyncio.run(test_async())

    def test_watchp_by_name(self):
        class MyObject:
            @rxvalue
            def a(self):
                return 1
        
        obj = MyObject()

        async def test_async():
            results = []
            async for value in watchp(obj, 'a'):
                results.append(value)
                if len(results) == 2:
                    break
                asyncio.create_task(self.change_value(obj))
            self.assertEqual(results, [1, 2])
            
        asyncio.run(test_async())

    def test_watchp_invalid_name(self):
        class MyObject:
            pass
        
        obj = MyObject()

        async def test_async():
            with self.assertRaises(ValueError):
                async for _ in watchp(obj, 'a'):
                    pass
        
        asyncio.run(test_async())

    async def change_value(self, obj):
        await asyncio.sleep(0.01)
        obj.a = 2

if __name__ == '__main__':
    unittest.main()
