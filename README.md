# rxprop
Super-simple reactive properties.


## Features
- Minimal API: 
- Developed for Python 3.12+
- No dependencies


## Installation

```bash
pip install rxprop # NOT YET!!
```


## Usage

See the [User Guide notebook](Samples/UserGuide.ipynb) for more details.

Declaring reactive properties:

```python
import rxprop as rx

class MyClass:
    
    @rx.value
    def my_value(self) -> int:
        return 1 # initial value
    
    @rx.computed
    def my_computed(self) -> int:
        return self.my_value * 2 # compute function

obj = MyClass()
```

Using reactive properties:

```python
import asyncio

async def consumer():
    async for i in rx.watch(obj, MyClass.my_value):
        print(i)

task = asyncio.create_task(consumer())

await asyncio.sleep(0)
obj.my_value = 2
await asyncio.sleep(0)

task.cancel()

# Output:
# | 2
# | 4
```
