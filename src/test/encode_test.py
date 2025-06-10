from __future__ import annotations

import typing
from dataclasses import dataclass
from datetime import datetime

from dataclass_extensions.encode import encode
from dataclass_extensions.types import *


class Employee(typing.NamedTuple):
    name: str
    id: int


class Point2D(typing.TypedDict):
    x: int
    y: int
    label: str


@dataclass
class Foo:
    x: int


def test_encode_with_a_variety_of_complex_types():
    @dataclass
    class Config:
        foo: Foo
        bar: Foo | None
        lr: float
        path: PathOrStr
        set_data: set[str]
        list_data: typing.List[Foo]
        fixed_tuple: tuple[int, int]
        indefinite_tuple: tuple[Foo, ...]
        employee: Employee
        point: Point2D
        time: datetime

    now = datetime.now()

    config = Config(
        foo=Foo(x=0),
        bar=None,
        lr=0.0,
        path="/path",
        set_data={"a"},
        list_data=[Foo(x=1)],
        fixed_tuple=(0, 1),
        indefinite_tuple=(Foo(x=-1),),
        employee=Employee(name="Bob", id=0),
        point=Point2D(x=0, y=0, label="first"),
        time=now,
    )

    encoded = encode(config)
    assert encoded == {
        "foo": {"x": 0},
        "bar": None,
        "lr": 0.0,
        "path": "/path",
        "set_data": ["a"],
        "list_data": [{"x": 1}],
        "fixed_tuple": [0, 1],
        "indefinite_tuple": [{"x": -1}],
        "employee": ["Bob", 0],
        "point": {"x": 0, "y": 0, "label": "first"},
        "time": now.timestamp(),
    }
