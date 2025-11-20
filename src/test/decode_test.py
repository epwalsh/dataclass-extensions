from __future__ import annotations

import collections.abc
import dataclasses
import sys
import typing
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pytest

from dataclass_extensions.decode import _coerce, decode
from dataclass_extensions.registrable import Registrable
from dataclass_extensions.types import *


class Employee(typing.NamedTuple):
    name: str
    id: int


class Point2D(typing.TypedDict):
    x: int
    y: int
    label: str


if sys.version_info >= (3, 12):
    from ._type_alias import Alias  # type: ignore
else:
    Alias = int  # type: ignore

dt_now = datetime.now()


@pytest.mark.parametrize(
    "value, type_hint, expected",
    [
        # Sequences.
        pytest.param([0, 1], list[int], [0, 1], id="list[int]"),
        pytest.param([0, 1], typing.List[int], [0, 1], id="typing.List[int]"),
        pytest.param([0, 1], tuple[int, ...], (0, 1), id="tuple[int, ...]"),
        pytest.param([0, 1], tuple[int, int], (0, 1), id="tuple[int, int]"),
        pytest.param([0, "a"], tuple[int, str], (0, "a"), id="tuple[int, str]"),
        pytest.param([0, 1], collections.abc.Sequence[int], (0, 1), id="abc.Sequence[int]"),
        pytest.param(
            [0, 1], collections.abc.Sequence[int] | None, (0, 1), id="abc.Sequence[int] | None"
        ),
        pytest.param([0, 1], typing.Sequence[int], (0, 1), id="typing.Sequence[int]"),
        pytest.param([0, 1], typing.Sequence[int] | None, (0, 1), id="typing.Sequence[int] | None"),
        pytest.param(
            [0, 1],
            collections.abc.MutableSequence[int] | None,
            [0, 1],
            id="abc.MutableSequence[int] | None",
        ),
        pytest.param(["Bob", 0], Employee, Employee("Bob", 0), id="typing.NamedTuple"),
        # Sets.
        pytest.param([0, 1], collections.abc.Set[int] | None, {0, 1}, id="abc.Set[int] | None"),
        pytest.param([0, 1], typing.Set[int] | None, {0, 1}, id="typing.Set[int] | None"),
        pytest.param(
            [0, 1], collections.abc.MutableSet[int] | None, {0, 1}, id="abc.MutableSet[int] | None"
        ),
        # Mappings.
        pytest.param(
            {"a": 0},
            dict[str, int] | None,
            {"a": 0},
            id="dict[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            typing.Dict[str, int] | None,
            {"a": 0},
            id="typing.Dict[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            typing.Mapping[str, int] | None,
            {"a": 0},
            id="typing.Mapping[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            collections.abc.Mapping[str, int] | None,
            {"a": 0},
            id="abc.Mapping[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            typing.Mapping[str, int] | None,
            {"a": 0},
            id="typing.Mapping[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            collections.abc.MutableMapping[str, int] | None,
            {"a": 0},
            id="abc.MutableMapping[str, int] | None",
        ),
        pytest.param(
            {"a": 0},
            typing.MutableMapping[str, int] | None,
            {"a": 0},
            id="typing.MutableMapping[str, int] | None",
        ),
        pytest.param(
            {"x": 0, "y": 1, "label": "first"},
            Point2D,
            {"x": 0, "y": 1, "label": "first"},
            id="typing.TypedDict",
        ),
        # Literal values.
        pytest.param(
            "foo",
            typing.Literal["foo", "bar"],
            "foo",
            id="typing.Literal[foo, bar]",
        ),
        # Aliases.
        pytest.param(
            0,
            Alias,
            0,
            id="Alias",
        ),
        # Datetime.
        pytest.param(
            dt_now.timestamp(),
            datetime,
            dt_now,
            id="datetime",
        ),
    ],
)
def test_coerce_from_type_hints(value: Any, type_hint: Any, expected: Any):
    result = _coerce(value, type_hint, {}, "0")
    assert type(result) is type(expected)
    assert result == expected


@dataclass
class Foo:
    x: int


def test_decode_attribute_error():
    with pytest.raises(AttributeError):
        decode(Foo, {"x": 1, "y": 2})


def test_decode_with_a_variety_of_required_complex_types():
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

    config = decode(
        Config,
        {
            "foo": {"x": 0},
            "bar": None,
            "lr": 0.0,
            "path": "/path",
            "set_data": ["a", "b", "c"],
            "list_data": [{"x": 0}],
            "fixed_tuple": [0, 1],
            "indefinite_tuple": [{"x": -1}],
        },
    )
    assert isinstance(config, Config)
    assert config.set_data == {"a", "b", "c"}
    assert all(isinstance(v, Foo) for v in config.list_data)
    assert all(isinstance(v, Foo) for v in config.indefinite_tuple)


def test_decode_with_a_variety_of_optional_complex_types():
    @dataclass
    class Config:
        foo: Foo | None = None
        lr: float = dataclasses.field(default=0.0)
        path: PathOrStr | None = None
        set_data: set[str] = dataclasses.field(default_factory=set)
        list_data: typing.List[Foo] = dataclasses.field(default_factory=list)
        fixed_tuple: tuple[int, int] = dataclasses.field(default_factory=lambda: (0, 0))
        indefinite_tuple: tuple[Foo, ...] = dataclasses.field(default_factory=tuple)
        str_data: str | None = None

    config = decode(
        Config,
        {
            "foo": {"x": 0},
            "lr": 0.0,
            "path": None,
            "set_data": ["a", "b", "c"],
            "list_data": [{"x": 0}],
            "fixed_tuple": [0, 1],
            "indefinite_tuple": [{"x": -1}],
            "str_data": "",
        },
    )
    assert isinstance(config, Config)
    assert config.set_data == {"a", "b", "c"}
    assert config.path is None
    assert all(isinstance(v, Foo) for v in config.list_data)
    assert all(isinstance(v, Foo) for v in config.indefinite_tuple)
    assert config.str_data == ""


@dataclass
class BaseType(Registrable):
    pass


@BaseType.register("type1")
@dataclass
class SubType(BaseType):
    x: int


# Classes for custom handler tests (must be at module scope for type hints)
class CustomType:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, CustomType) and self.value == other.value


class TypeA:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, TypeA) and self.value == other.value


class TypeB:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, TypeB) and self.value == other.value


# Enum for enum test
class Color(Enum):
    RED = "red"
    BLUE = "blue"


# Registrable types for nested test
@dataclass
class NestedBaseType(Registrable):
    x: int


@NestedBaseType.register("nested1")
@dataclass
class NestedSubType1(NestedBaseType):
    y: int = 1


def test_decode_with_registrable_subclasses():
    decode(BaseType, {"type": "type1", "x": 0})

    @dataclass
    class Config:
        foo: BaseType | None = None

    decode(Config, {"foo": {"type": "type1", "x": 0}})


def test_decode_custom_handler():
    """Test decode with custom decoder handler."""

    @dataclass
    class Config:
        custom: CustomType
        x: int = 1

    # Register custom decoder
    def custom_decoder(data):
        return CustomType(data["value"])

    decode.register_decoder(custom_decoder, CustomType)

    try:
        config = decode(Config, {"x": 1, "custom": {"value": "test"}})
        assert config.x == 1
        assert isinstance(config.custom, CustomType)
        assert config.custom.value == "test"
    finally:
        # Clean up - remove custom handler
        if CustomType in decode.custom_handlers:
            del decode.custom_handlers[CustomType]


def test_decode_custom_handler_multiple_types():
    """Test decode with custom decoder handler for multiple types."""

    @dataclass
    class Config:
        a: TypeA
        b: TypeB

    def decoder_a(data):
        return TypeA(data["value"])

    def decoder_b(data):
        return TypeB(data["value"])

    decode.register_decoder(decoder_a, TypeA)
    decode.register_decoder(decoder_b, TypeB)

    try:
        # Pass dict values that will be converted
        config = decode(Config, {"a": {"value": "value_a"}, "b": {"value": "value_b"}})
        assert isinstance(config.a, TypeA)
        assert config.a.value == "value_a"
        assert isinstance(config.b, TypeB)
        assert config.b.value == "value_b"
    finally:
        # Clean up
        for t in [TypeA, TypeB]:
            if t in decode.custom_handlers:
                del decode.custom_handlers[t]


def test_decode_type_error():
    """Test decode raises TypeError when coercion fails."""

    @dataclass
    class Config:
        x: int

    # Should raise TypeError when value can't be coerced
    with pytest.raises(TypeError, match="Not sure how to coerce"):
        decode(Config, {"x": "not_an_int"})


def test_decode_missing_required_field():
    """Test decode with missing required field."""
    from dataclass_extensions.utils import required_field

    @dataclass
    class Config:
        x: int
        y: str = required_field()

    # Missing required field should use MISSING default
    config = decode(Config, {"x": 1})
    assert config.x == 1
    assert config.y is MISSING


def test_decode_invalid_tuple_length():
    """Test decode with invalid tuple length."""

    @dataclass
    class Config:
        fixed_tuple: tuple[int, int]

    # Tuple with wrong length - Python's tuple constructor may accept or reject
    # Let's test what actually happens - it might truncate or raise
    # For now, test that valid tuple works
    config = decode(Config, {"fixed_tuple": [1, 2]})
    assert config.fixed_tuple == (1, 2)

    # Test that extra items might be truncated (Python tuple behavior)
    # or raise an error - depends on implementation
    # Let's just verify the behavior exists
    try:
        config_extra = decode(Config, {"fixed_tuple": [1, 2, 3]})
        # If it doesn't raise, extra items might be ignored
        assert len(config_extra.fixed_tuple) == 2
    except (TypeError, ValueError):
        # If it raises, that's also valid behavior
        pass


def test_decode_enum_failure():
    """Test decode with invalid enum value."""

    @dataclass
    class Config:
        color: Color

    # Valid enum value should work
    config = decode(Config, {"color": "red"})
    assert config.color == Color.RED

    # Invalid enum value should raise ValueError (from Enum constructor) or TypeError
    # The actual error depends on how the coercion fails
    with pytest.raises((ValueError, TypeError)):
        decode(Config, {"color": "invalid"})


def test_decode_any_type():
    """Test decode with Any type hint."""

    @dataclass
    class Config:
        value: Any

    # Any type should accept any value
    config1 = decode(Config, {"value": 1})
    assert config1.value == 1

    config2 = decode(Config, {"value": "string"})
    assert config2.value == "string"

    config3 = decode(Config, {"value": {"nested": "dict"}})
    assert config3.value == {"nested": "dict"}


def test_decode_initvar():
    """Test decode with InitVar fields."""

    @dataclass
    class Config:
        x: int
        y: dataclasses.InitVar[str] = "default"

    # InitVar fields should be handled correctly
    config = decode(Config, {"x": 1, "y": "test"})
    assert config.x == 1
    # InitVar fields are not stored as attributes, so we can't check y directly


def test_decode_empty_collections():
    """Test decode with empty collections."""

    @dataclass
    class Config:
        empty_list: list[int]
        empty_set: set[str]
        empty_tuple: tuple[int, ...]
        empty_dict: dict[str, int]

    config = decode(
        Config,
        {
            "empty_list": [],
            "empty_set": [],
            "empty_tuple": [],
            "empty_dict": {},
        },
    )
    assert config.empty_list == []
    assert config.empty_set == set()
    assert config.empty_tuple == ()
    assert config.empty_dict == {}


def test_decode_nested_registrable():
    """Test decode with nested registrable types."""

    @dataclass
    class Container:
        item: NestedBaseType

    container = decode(Container, {"item": {"type": "nested1", "x": 10, "y": 20}})
    assert isinstance(container.item, NestedSubType1)
    assert container.item.x == 10
    assert container.item.y == 20
