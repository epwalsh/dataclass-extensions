from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

from .decode import DecodeError, _coerce, _get_type_hints
from .types import Dataclass

C = TypeVar("C", bound=Dataclass)


def merge(instance: C, *dicts: dict[str, Any]) -> C:
    """
    Merge one or more unstructured dictionaries into a dataclass, returning a new
    instance of the same type. The original instance is not modified.

    When a dictionary value is itself a dict and the corresponding field on the
    instance is already a dataclass, the merge is applied recursively.

    :raises DecodeError: If a key in a dictionary is not a valid field name, or if
        a value cannot be coerced to the expected type.
    """
    cls = type(instance)
    type_hints = _get_type_hints(cls)

    # Collect current values for all init fields.
    current: dict[str, Any] = {}
    for f in dataclasses.fields(instance):  # type: ignore[arg-type]
        if f.init:
            current[f.name] = getattr(instance, f.name)

    for d in dicts:
        for key, value in d.items():
            if key not in type_hints:
                raise DecodeError(f"class '{cls.__qualname__}' has no attribute '{key}'")

            existing = current[key]

            # Recursively merge when the incoming value is a dict and the existing
            # value is a dataclass instance (not a dataclass class/type).
            if (
                isinstance(value, dict)
                and dataclasses.is_dataclass(existing)
                and not isinstance(existing, type)
            ):
                current[key] = merge(existing, value)
            else:
                current[key] = _coerce(value, type_hints[key], {}, key, cls)

    return cls(**current)
