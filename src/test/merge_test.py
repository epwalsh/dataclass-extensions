from __future__ import annotations

from dataclasses import dataclass

import pytest

from dataclass_extensions.decode import DecodeError
from dataclass_extensions.merge import merge, merge_from_dotlist


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


# ---------------------------------------------------------------------------
# merge_from_dotlist tests
# ---------------------------------------------------------------------------


@dataclass
class Optimizer:
    lr: float
    steps: int


@dataclass
class TrainConfig:
    optimizer: Optimizer
    name: str = "default"
    seed: int = 42


def test_dotlist_basic():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg, "name=run1")
    assert result.name == "run1"
    assert result.optimizer.lr == 0.1  # unchanged


def test_dotlist_nested():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg, "optimizer.lr=0.001")
    assert result.optimizer.lr == 0.001
    assert result.optimizer.steps == 100  # unchanged


def test_dotlist_multiple_overrides():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg, "optimizer.lr=0.001", "optimizer.steps=500", "name=run2")
    assert result.optimizer.lr == 0.001
    assert result.optimizer.steps == 500
    assert result.name == "run2"


def test_dotlist_yaml_types():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    # int
    result = merge_from_dotlist(cfg, "seed=7")
    assert result.seed == 7
    assert type(result.seed) is int
    # float written as scientific notation
    result = merge_from_dotlist(cfg, "optimizer.lr=1e-4")
    assert result.optimizer.lr == 1e-4

    # bool
    @dataclass
    class Cfg2:
        flag: bool

    result2 = merge_from_dotlist(Cfg2(flag=False), "flag=true")
    assert result2.flag is True


def test_dotlist_yaml_list_value():
    @dataclass
    class Cfg:
        items: list[int]

    result = merge_from_dotlist(Cfg(items=[1, 2]), "items=[3, 4, 5]")
    assert result.items == [3, 4, 5]


def test_dotlist_yaml_null():
    @dataclass
    class Cfg:
        value: int | None = 1

    result = merge_from_dotlist(Cfg(), "value=null")
    assert result.value is None


def test_dotlist_string_with_spaces():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg, "name=my experiment run")
    assert result.name == "my experiment run"


def test_dotlist_does_not_modify_original():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    merge_from_dotlist(cfg, "optimizer.lr=0.001", "name=run2")
    assert cfg.optimizer.lr == 0.1
    assert cfg.name == "default"


def test_dotlist_no_overrides():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg)
    assert result == cfg
    assert result is not cfg


def test_dotlist_missing_equals_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(ValueError, match="expected the form"):
        merge_from_dotlist(cfg, "optimizer.lr")


def test_dotlist_unknown_field_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(DecodeError, match="has no attribute 'nonexistent'"):
        merge_from_dotlist(cfg, "nonexistent=1")


def test_dotlist_unknown_nested_field_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(DecodeError, match="has no attribute 'momentum'"):
        merge_from_dotlist(cfg, "optimizer.momentum=0.9")


def test_dotlist_type_coercion_error_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(DecodeError):
        merge_from_dotlist(cfg, "optimizer.steps=not_a_number")


def test_dotlist_conflicting_leaf_and_nested_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(ValueError, match="Conflicting overrides"):
        merge_from_dotlist(cfg, "optimizer=something", "optimizer.lr=0.001")


def test_dotlist_double_dash_prefix():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    result = merge_from_dotlist(cfg, "--optimizer.lr=0.001", "--name=run2")
    assert result.optimizer.lr == 0.001
    assert result.name == "run2"


def test_dotlist_single_dash_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(ValueError, match="expected the form"):
        merge_from_dotlist(cfg, "-optimizer.lr=0.001")


def test_dotlist_triple_dash_raises():
    cfg = TrainConfig(optimizer=Optimizer(lr=0.1, steps=100))
    with pytest.raises(ValueError, match="expected the form"):
        merge_from_dotlist(cfg, "---optimizer.lr=0.001")


def test_dotlist_value_containing_equals():
    @dataclass
    class Cfg:
        expr: str

    # The value part should include everything after the first '='
    result = merge_from_dotlist(Cfg(expr=""), "expr=a=b")
    assert result.expr == "a=b"


# ---------------------------------------------------------------------------
# sequence index targeting tests
# ---------------------------------------------------------------------------


def test_dotlist_sequence_index_tuple():
    @dataclass
    class Cfg:
        x: tuple[int, int]

    result = merge_from_dotlist(Cfg(x=(0, 1)), "--x.0=-1")
    assert result.x == (-1, 1)


def test_dotlist_sequence_index_list():
    @dataclass
    class Cfg:
        items: list[int]

    result = merge_from_dotlist(Cfg(items=[10, 20, 30]), "items.1=99")
    assert result.items == [10, 99, 30]


def test_dotlist_sequence_index_multiple():
    @dataclass
    class Cfg:
        x: tuple[int, int, int]

    result = merge_from_dotlist(Cfg(x=(0, 1, 2)), "x.0=7", "x.2=9")
    assert result.x == (7, 1, 9)


def test_dotlist_sequence_index_does_not_modify_original():
    @dataclass
    class Cfg:
        x: tuple[int, int]

    original = Cfg(x=(0, 1))
    merge_from_dotlist(original, "x.0=99")
    assert original.x == (0, 1)


def test_merge_sequence_by_index_directly():
    @dataclass
    class Cfg:
        items: list[float]

    result = merge(Cfg(items=[1.0, 2.0, 3.0]), {"items": {1: 9.9}})
    assert result.items[1] == 9.9
    assert result.items[0] == 1.0
    assert result.items[2] == 3.0
