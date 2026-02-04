from __future__ import annotations

import pickle
from dataclasses import dataclass

import pytest

from dataclass_extensions import Registrable, encode


def test_registrable_class():
    @dataclass
    class BaseType(Registrable):
        x: int
        y: int = -1
        z: int = -1

    @BaseType.register("bar")
    @dataclass
    class SubType(BaseType):
        w: int = 2

    assert SubType.registered_base == BaseType  # type: ignore
    assert SubType.registered_name == "bar"  # type: ignore
    assert SubType.get_registered_name() == "bar"

    assert not isinstance(BaseType(x=0), SubType)
    assert isinstance(BaseType(x=0, type="bar"), SubType)
    assert isinstance(SubType(x=0), SubType)

    assert encode(SubType(x=0)) == {"x": 0, "y": -1, "z": -1, "w": 2, "type": "bar"}


def test_registrable_class_with_default():
    @dataclass
    class BaseType(Registrable):
        x: int
        y: int = -1
        z: int = -1

    @BaseType.register("default", default=True)
    @dataclass
    class DefaultType(BaseType):
        w: int = 2

    assert BaseType.get_default() is DefaultType
    assert isinstance(BaseType(x=0), DefaultType)


def test_registrable_duplicate_default():
    """Test that registering duplicate defaults raises ValueError."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("default1", default=True)
    @dataclass
    class DefaultType1(BaseType):
        pass

    # Trying to register another default should raise ValueError
    with pytest.raises(ValueError, match="A default implementation"):

        @BaseType.register("default2", default=True)
        @dataclass
        class DefaultType2(BaseType):
            pass


def test_registrable_invalid_type_name():
    """Test that using invalid type name raises KeyError."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("valid")
    @dataclass
    class ValidType(BaseType):
        pass

    # Using invalid type name should raise KeyError
    with pytest.raises(KeyError, match="'invalid' is not registered name"):
        BaseType(x=0, type="invalid")


def test_registrable_get_registered_class_error():
    """Test get_registered_class raises KeyError for invalid type."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("valid")
    @dataclass
    class ValidType(BaseType):
        pass

    with pytest.raises(KeyError, match="'invalid' is not registered name"):
        BaseType.get_registered_class("invalid")


def test_registrable_get_registered_name_error():
    """Test get_registered_name raises ValueError for non-registered class."""

    @dataclass
    class BaseType(Registrable):
        x: int

    # Base class itself is not registered
    with pytest.raises(ValueError, match="is not a registered subclass"):
        BaseType.get_registered_name()


def test_registrable_get_default_error():
    """Test get_default raises ValueError when no default is registered."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("not_default")
    @dataclass
    class NotDefaultType(BaseType):
        pass

    with pytest.raises(ValueError, match="A default implementation"):
        BaseType.get_default()


def test_registrable_register_non_subclass():
    """Test that registering a non-subclass raises TypeError."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @dataclass
    class NotSubclass:
        y: int

    with pytest.raises(TypeError, match="must be a subclass"):
        BaseType.register("invalid")(NotSubclass)  # type: ignore


def test_registrable_get_registered_names():
    """Test get_registered_names returns list of registered names."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("type1")
    @dataclass
    class Type1(BaseType):
        pass

    @BaseType.register("type2")
    @dataclass
    class Type2(BaseType):
        pass

    names = BaseType.get_registered_names()
    assert set(names) == {"type1", "type2"}


def test_registrable_get_registered_name_with_subclass():
    """Test get_registered_name with subclass parameter."""

    @dataclass
    class BaseType(Registrable):
        x: int

    @BaseType.register("type1")
    @dataclass
    class Type1(BaseType):
        pass

    @BaseType.register("type2")
    @dataclass
    class Type2(BaseType):
        pass

    assert BaseType.get_registered_name(Type1) == "type1"
    assert BaseType.get_registered_name(Type2) == "type2"

    with pytest.raises(ValueError, match="is not a registered subclass"):
        BaseType.get_registered_name(BaseType)


def test_registrable_nested_registrable():
    """Test nested registrable types."""

    @dataclass
    class OuterBase(Registrable):
        x: int

    @OuterBase.register("outer1")
    @dataclass
    class Outer1(OuterBase):
        y: int = 1

    @dataclass
    class InnerBase(Registrable):
        z: int

    @InnerBase.register("inner1")
    @dataclass
    class Inner1(InnerBase):
        w: int = 2

    @dataclass
    class Container:
        outer: OuterBase
        inner: InnerBase

    container = Container(outer=Outer1(x=10, y=20), inner=Inner1(z=30, w=40))
    assert isinstance(container.outer, Outer1)
    assert isinstance(container.inner, Inner1)
    assert container.outer.x == 10
    assert container.outer.y == 20
    assert container.inner.z == 30
    assert container.inner.w == 40


@dataclass
class Foo(Registrable):
    x: int
    y: str


@Foo.register("bar")
@dataclass
class Bar(Foo):
    z: float


def test_registrable_is_pickleable():
    bar = pickle.loads(pickle.dumps(Bar(x=10, y="hello", z=3.14)))
    assert isinstance(bar, Bar)
