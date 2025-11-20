from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass
from datetime import datetime

import pytest

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


def test_encode_exclude_none():
    """Test encode with exclude_none=True."""

    @dataclass
    class Config:
        x: int | None = None
        y: str = "test"
        z: int | None = None

    config = Config(x=None, y="test", z=None)
    encoded = encode(config, exclude_none=True)
    assert encoded == {"y": "test"}
    assert "x" not in encoded
    assert "z" not in encoded

    # With exclude_none=False, None values should be included
    encoded_all = encode(config, exclude_none=False)
    assert encoded_all == {"x": None, "y": "test", "z": None}


def test_encode_exclude_private_fields():
    """Test encode with exclude_private_fields=True."""

    @dataclass
    class Config:
        x: int = 1
        _private: int = 2
        y: str = "test"
        __very_private: str = "hidden"  # type: ignore

    config = Config()
    encoded = encode(config, exclude_private_fields=True)
    assert encoded == {"x": 1, "y": "test"}
    assert "_private" not in encoded
    # Python name-mangles __very_private to _Config__very_private
    assert "_Config__very_private" not in encoded

    # With exclude_private_fields=False, private fields should be included
    # Note: Python name-mangles __very_private to _Config__very_private
    encoded_all = encode(config, exclude_private_fields=False)
    assert encoded_all == {"x": 1, "_private": 2, "y": "test", "_Config__very_private": "hidden"}


def test_encode_recurse():
    """Test encode with recurse=False."""

    @dataclass
    class Inner:
        x: int = 1

    @dataclass
    class Config:
        inner: Inner
        y: str = "test"

    config = Config(inner=Inner(x=2), y="test")

    # With recurse=True (default), inner dataclass is encoded as dict
    encoded_recurse = encode(config, recurse=True)
    assert encoded_recurse == {"inner": {"x": 2}, "y": "test"}
    assert isinstance(encoded_recurse["inner"], dict)

    # With recurse=False, inner dataclass is kept as object
    encoded_no_recurse = encode(config, recurse=False)
    assert encoded_no_recurse == {"inner": Inner(x=2), "y": "test"}
    assert isinstance(encoded_no_recurse["inner"], Inner)


def test_encode_strict():
    """Test encode with strict=False."""

    class CustomClass:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return f"Custom({self.value})"

    @dataclass
    class Config:
        custom: CustomClass
        x: int = 1

    config = Config(x=1, custom=CustomClass("test"))

    # With strict=True (default), should raise TypeError
    with pytest.raises(TypeError, match="not sure how to encode"):
        encode(config, strict=True)

    # With strict=False, should use str() as fallback
    encoded = encode(config, strict=False)
    assert encoded == {"x": 1, "custom": "Custom(test)"}


def test_encode_custom_handler():
    """Test encode with custom encoder handler."""

    class CustomType:
        def __init__(self, value):
            self.value = value

    @dataclass
    class Config:
        custom: CustomType
        x: int = 1

    config = Config(x=1, custom=CustomType("test"))

    # Register custom encoder
    def custom_encoder(obj):
        return {"custom_value": obj.value}

    encode.register_encoder(custom_encoder, CustomType)

    try:
        encoded = encode(config)
        assert encoded == {"x": 1, "custom": {"custom_value": "test"}}
    finally:
        # Clean up - remove custom handler
        if CustomType in encode.custom_handlers:
            del encode.custom_handlers[CustomType]


def test_encode_custom_handler_multiple_types():
    """Test encode with custom encoder handler for multiple types."""

    class TypeA:
        def __init__(self, value):
            self.value = value

    class TypeB:
        def __init__(self, value):
            self.value = value

    @dataclass
    class Config:
        a: TypeA
        b: TypeB

    config = Config(a=TypeA("a"), b=TypeB("b"))

    def custom_encoder(obj):
        return f"encoded_{obj.value}"

    encode.register_encoder(custom_encoder, TypeA, TypeB)

    try:
        encoded = encode(config)
        assert encoded == {"a": "encoded_a", "b": "encoded_b"}
    finally:
        # Clean up
        for t in [TypeA, TypeB]:
            if t in encode.custom_handlers:
                del encode.custom_handlers[t]


def test_encode_empty_collections():
    """Test encode with empty collections."""

    @dataclass
    class Config:
        empty_list: list[int] = dataclasses.field(default_factory=list)
        empty_set: set[str] = dataclasses.field(default_factory=set)
        empty_tuple: tuple = dataclasses.field(default_factory=tuple)
        empty_dict: dict[str, int] = dataclasses.field(default_factory=dict)

    config = Config()
    encoded = encode(config)
    assert encoded == {
        "empty_list": [],
        "empty_set": [],
        "empty_tuple": [],
        "empty_dict": {},
    }


def test_encode_nested_registrable():
    """Test encode with nested registrable types."""
    from dataclass_extensions import Registrable

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("sub1")
    @dataclass
    class SubType1(BaseType):
        y: int = 1

    @BaseType.register("sub2")
    @dataclass
    class SubType2(BaseType):
        z: int = 2

    @dataclass
    class Container:
        item: BaseType

    container = Container(item=SubType1(x=10, y=20))
    encoded = encode(container)
    assert encoded == {"item": {"x": 10, "y": 20, "type": "sub1"}}
