from __future__ import annotations

import collections.abc
import dataclasses
import sys
import typing
from dataclasses import dataclass
from datetime import datetime
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
        },
    )
    assert isinstance(config, Config)
    assert config.set_data == {"a", "b", "c"}
    assert config.path is None
    assert all(isinstance(v, Foo) for v in config.list_data)
    assert all(isinstance(v, Foo) for v in config.indefinite_tuple)


@dataclass
class BaseType(Registrable):
    pass


@BaseType.register("type1")
@dataclass
class SubType(BaseType):
    x: int


def test_decode_with_registrable_subclasses():
    @dataclass
    class Config:
        foo: BaseType | None = None

    decode(Config, {"foo": {"type": "type1", "x": 0}})
