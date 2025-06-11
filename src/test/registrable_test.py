from __future__ import annotations

from dataclasses import dataclass

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
