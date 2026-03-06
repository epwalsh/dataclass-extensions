from __future__ import annotations

from dataclasses import dataclass

import pytest

from dataclass_extensions.decode import DecodeError
from dataclass_extensions.merge import merge


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Config:
    lr: float
    steps: int
    name: str = "default"


@dataclass
class Inner:
    a: int
    b: int


@dataclass
class Outer:
    inner: Inner
    tag: str


def test_merge_basic():
    foo = merge(Point(x=1, y=2), {"y": 0})
    assert foo.x == 1
    assert foo.y == 0


def test_merge_does_not_modify_original():
    original = Point(x=1, y=2)
    _ = merge(original, {"y=": 0} if False else {"y": 0})
    result = merge(original, {"y": 99})
    assert original.y == 2
    assert result.y == 99


def test_merge_returns_new_instance():
    original = Point(x=1, y=2)
    result = merge(original, {"x": 10})
    assert result is not original


def test_merge_same_type():
    original = Point(x=1, y=2)
    result = merge(original, {"x": 10})
    assert type(result) is type(original)


def test_merge_multiple_dicts():
    original = Config(lr=0.1, steps=100)
    result = merge(original, {"lr": 0.01}, {"steps": 200, "name": "run1"})
    assert result.lr == 0.01
    assert result.steps == 200
    assert result.name == "run1"


def test_merge_later_dict_wins():
    original = Point(x=1, y=2)
    result = merge(original, {"x": 10}, {"x": 20})
    assert result.x == 20


def test_merge_empty_dict():
    original = Point(x=1, y=2)
    result = merge(original, {})
    assert result == original
    assert result is not original


def test_merge_no_dicts():
    original = Point(x=1, y=2)
    result = merge(original)
    assert result == original


def test_merge_recursive():
    original = Outer(inner=Inner(a=1, b=2), tag="v1")
    result = merge(original, {"inner": {"b": 99}})
    assert result.inner.a == 1
    assert result.inner.b == 99
    assert result.tag == "v1"


def test_merge_recursive_preserves_inner_original():
    inner = Inner(a=1, b=2)
    original = Outer(inner=inner, tag="v1")
    merge(original, {"inner": {"b": 99}})
    assert inner.b == 2  # original inner not modified


def test_merge_recursive_full_replace_with_dict():
    # A full dict for a nested dataclass field should still work recursively
    original = Outer(inner=Inner(a=1, b=2), tag="v1")
    result = merge(original, {"inner": {"a": 10, "b": 20}})
    assert result.inner.a == 10
    assert result.inner.b == 20


def test_merge_unknown_field_raises():
    with pytest.raises(DecodeError, match="has no attribute 'z'"):
        merge(Point(x=1, y=2), {"z": 0})


def test_merge_type_coercion_error_raises():
    with pytest.raises(DecodeError):
        merge(Point(x=1, y=2), {"x": "not_an_int"})


def test_merge_coerces_compatible_types():
    # int field accepts float that is a whole number
    result = merge(Point(x=1, y=2), {"x": 3.0})
    assert result.x == 3
    assert type(result.x) is int


def test_merge_optional_field():
    @dataclass
    class Cfg:
        value: int | None = None

    result = merge(Cfg(value=None), {"value": 42})
    assert result.value == 42

    result2 = merge(Cfg(value=42), {"value": None})
    assert result2.value is None


@dataclass
class Level3:
    z: int


@dataclass
class Level2:
    level3: Level3
    w: int


@dataclass
class Level1:
    level2: Level2
    v: int


def test_merge_deeply_nested():
    original = Level1(level2=Level2(level3=Level3(z=1), w=2), v=3)
    result = merge(original, {"level2": {"level3": {"z": 99}}})
    assert result.level2.level3.z == 99
    assert result.level2.w == 2
    assert result.v == 3


def test_merge_list_field_replaced():
    @dataclass
    class Cfg:
        items: list[int]

    original = Cfg(items=[1, 2, 3])
    result = merge(original, {"items": [4, 5]})
    assert result.items == [4, 5]
    assert original.items == [1, 2, 3]
