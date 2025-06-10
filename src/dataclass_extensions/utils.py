from __future__ import annotations

import dataclasses
import typing
from typing import Type, TypeVar

from .types import *

T = TypeVar("T")


@typing.overload
def required_field(name: str, *, strict: bool = False) -> T:  # type: ignore[type-var]
    ...


@typing.overload
def required_field() -> T:  # type: ignore[type-var]
    ...


def required_field(name: str | None = None, *, strict: bool = False, _: Type[T] | None = None) -> T:
    """
    Can be used in place of ``dataclasses.field()`` to mark a field required when non-default
    fields are not allowed.
    """
    if strict:
        if name is None:
            raise ValueError("'name' is required for a required_field with 'strict=True'")

        def err_out():
            raise ValueError(f"missing required field '{name}'")

        return typing.cast(T, dataclasses.field(default_factory=err_out))

    return typing.cast(T, dataclasses.field(default=MISSING))
