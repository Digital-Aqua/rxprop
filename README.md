# rxprop
Super-simple reactive properties.


## Features
- Minimal API: just `@value`, `@computed`, `watchf`, and `watchp`
- Designed for `asyncio`
- Developed for Python 3.12+
- No dependencies


## Installation

```bash
pip install rxprop # NOT PUBLISHED YET!!
```


## Usage

See the [User Guide notebook](Samples/UserGuide.ipynb) for more details.

Declare reactive properties with `@value` and `@computed`:

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

Subscribe to reactive properties with `watchp` and `watchf`, using an async iterator pattern:

```python
import asyncio

async def consumer():
    async for i in rx.watchp(obj, MyClass.my_value):
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


## Testing

Set up a conda environment:

```bash
conda create --prefix .conda --yes
conda env update --prefix .conda --file environment.yaml
```

Run the tests:

```bash
pytest .
```

## Roadmap

- Robust error handling
