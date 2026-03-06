dataclass-extensions
====================

Additional functionality for Python dataclasses

## Installation

Python 3.10 or newer is required. You can install the package from PyPI:

```fish
pip install dataclass-extensions
```

## Features

### Encode/decode to/from JSON-safe dictionaries

```python
from dataclasses import dataclass
from dataclass_extensions import decode, encode


@dataclass
class Fruit:
    calories: int
    price: float

@dataclass
class FruitBasket:
    fruit: Fruit
    count: int

basket = FruitBasket(fruit=Fruit(calories=200, price=1.0), count=2)
assert encode(basket) == {"fruit": {"calories": 200, "price": 1.0}, "count": 2}
assert decode(FruitBasket, encode(basket)) == basket
```

You can also define how to encode/decode non-dataclass types:

```python
from dataclasses import dataclass
from dataclass_extensions import decode, encode


class Foo:
    def __init__(self, x: int):
        self.x = x

@dataclass
class Bar:
    foo: Foo

encode.register_encoder(lambda foo: {"x": foo.x}, Foo)
decode.register_decoder(lambda d: Foo(d["x"]), Foo)

bar = Bar(foo=Foo(10))
assert encode(bar) == {"foo": {"x": 10}}
assert decode(Bar, encode(bar)) == bar
```

### Merge dictionaries into a dataclass

```python
from dataclasses import dataclass
from dataclass_extensions import merge


@dataclass
class Optimizer:
    lr: float
    steps: int

@dataclass
class Config:
    optimizer: Optimizer
    name: str = "default"

config = Config(optimizer=Optimizer(lr=0.1, steps=100), name="run1")

# Override top-level fields
updated = merge(config, {"name": "run2"})
assert updated.name == "run2"
assert updated.optimizer.lr == 0.1  # unchanged

# Merge recursively into nested dataclasses
updated = merge(config, {"optimizer": {"lr": 0.001}})
assert updated.optimizer.lr == 0.001
assert updated.optimizer.steps == 100  # unchanged
assert updated.name == "run1"          # unchanged

# The original is never modified
assert config.optimizer.lr == 0.1
```

### Override dataclass fields from the command line

`merge_from_dotlist()` works like `merge()` but accepts strings of the form
`"field=value"`, where the value is parsed as YAML. Nested fields are targeted
with dot notation. This gives you a cheap way to expose a dataclass config to a
CLI:

```python
import sys
from dataclasses import dataclass
from dataclass_extensions import merge_from_dotlist


@dataclass
class Optimizer:
    lr: float = 1e-3
    steps: int = 1000

@dataclass
class Config:
    optimizer: Optimizer = None  # type: ignore
    name: str = "default"
    seed: int = 42

    def __post_init__(self):
        if self.optimizer is None:
            self.optimizer = Optimizer()

# Both "field=value" and "--field=value" forms are accepted, so this works
# whether argv looks like ["optimizer.lr=1e-4", "name=run1"] or
# ["--optimizer.lr=1e-4", "--name=run1"].
config = merge_from_dotlist(Config(), sys.argv[1:])

# Values are parsed as YAML, so types are handled automatically:
assert config.optimizer.lr  == 0.0001  (float)
assert config.optimizer.steps == 500   (int)
assert config.name == "run1"           (str)
```

Supported value syntax includes plain scalars (`0.001`, `100`, `true`, `null`), quoted strings (`"hello world"`), lists (`[1, 2, 3]`), and inline mappings (`{a: 1}`).
Values containing `=` work correctly because the split happens on the first `=` only.

### Polymorphism through registrable subclasses

```python
from dataclasses import dataclass
from dataclass_extensions import Registrable, decode, encode


@dataclass
class Fruit(Registrable):
    calories: int
    price: float

@Fruit.register("banana")
@dataclass
class Banana(Fruit):
    calories: int = 200
    price: float = 1.25

@Fruit.register("apple")
@dataclass
class Apple(Fruit):
    calories: int = 150
    price: float = 1.50
    variety: str = "Granny Smith"

@dataclass
class FruitBasket:
    fruit: Fruit
    count: int

basket = FruitBasket(fruit=Apple(), count=2)
assert encode(basket) == {
    "fruit": {
        "type": "apple",  # corresponds to the registered name
        "calories": 150,
        "price": 1.5,
        "variety": "Granny Smith",
    },
    "count": 2,
}
assert decode(FruitBasket, encode(basket)) == basket
```
