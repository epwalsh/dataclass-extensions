dataclass-extensions
====================

Additional functionality for Python dataclasses

## Installation

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

### Registrable subclasses

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


@dataclass
class FruitBasket:
    fruit: Fruit
    count: int


basket = FruitBasket(fruit=Apple(), count=2)
assert encode(basket) == {"fruit": {"calories": 150, "price": 1.5, "type": "apple"}, "count": 2}
assert decode(FruitBasket, encode(basket)) == basket
```
