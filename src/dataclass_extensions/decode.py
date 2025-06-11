from __future__ import annotations

import collections.abc
import dataclasses
import types
import typing
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Type, TypeVar

from .registrable import Registrable
from .types import *

C = TypeVar("C", bound=Dataclass)


class Decoder:
    custom_handlers: ClassVar[dict[Any, Callable[[Any], Any]]] = {}

    def register_decoder(self, encoder_fun: Callable[[Any], Any], *target_types: Any):
        for type in target_types:
            self.custom_handlers[type] = encoder_fun

    def __call__(self, config_class: Type[C], data: dict[str, Any]) -> C:
        """
        Decode a dataset from a JSON-safe dictionary. The inverse of :func:`encode()`.
        """
        type_hints = typing.get_type_hints(config_class)
        kwargs = {k: _coerce(v, type_hints[k], self.custom_handlers, k) for k, v in data.items()}
        return config_class(**kwargs)


decode = Decoder()


def _get_types(type_hint: Any) -> tuple[Any, ...]:
    # NOTE: 'types.UnionType' doesn't cover union types with 'typing.*' types.
    if _safe_isinstance(type_hint, (types.UnionType, type(typing.List | None))):
        return type_hint.__args__
    elif _safe_isinstance(type_hint, dataclasses.InitVar):
        return _get_types(type_hint.type)
    # TypeAliasType added in 3.12
    elif hasattr(typing, "TypeAliasType") and _safe_isinstance(type_hint, typing.TypeAliasType):  # type: ignore
        return _get_types(type_hint.__value__)
    else:
        return (type_hint,)


def _safe_isinstance(a, b) -> bool:
    try:
        return isinstance(a, b)
    except TypeError:
        return False


def _safe_issubclass(a, b) -> bool:
    try:
        return issubclass(a, b)
    except TypeError:
        return False


def _coerce(
    value: Any, type_hint: Any, custom_handlers: dict[Any, Callable[[Any], Any]], key: str
) -> Any:
    if value is MISSING:
        raise ValueError(f"Missing required field at '{key}'")

    if type_hint in custom_handlers:
        return custom_handlers[type_hint](value)

    allowed_types = _get_types(type_hint)
    for allowed_type in allowed_types:
        if allowed_type in custom_handlers:
            return custom_handlers[allowed_type](value)

        if _safe_isinstance(value, allowed_type):
            return value

        if _safe_issubclass(allowed_type, Enum):
            try:
                return allowed_type(value)
            except TypeError:
                pass

        # e.g. typing.NamedTuple
        if _safe_issubclass(allowed_type, tuple) and _safe_isinstance(value, (list, tuple)):
            try:
                return allowed_type(*value)
            except TypeError:
                pass

        if _safe_issubclass(allowed_type, datetime) and _safe_isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except TypeError:
                pass

        origin = getattr(allowed_type, "__origin__", None)
        args = getattr(allowed_type, "__args__", None)
        if (origin is list or origin is collections.abc.MutableSequence) and _safe_isinstance(
            value, (list, tuple)
        ):
            if args:
                return [
                    _coerce(v, args[0], custom_handlers, f"{key}.{i}") for i, v in enumerate(value)
                ]
            else:
                return list(value)
        elif (
            origin is set or origin is collections.abc.Set or origin is collections.abc.MutableSet
        ) and _safe_isinstance(value, (list, tuple, set)):
            if args:
                return set(
                    _coerce(v, args[0], custom_handlers, f"{key}.{i}") for i, v in enumerate(value)
                )
            else:
                return set(value)
        elif origin is collections.abc.Sequence and _safe_isinstance(value, (list, tuple)):
            if args:
                return tuple(
                    [
                        _coerce(v, args[0], custom_handlers, f"{key}.{i}")
                        for i, v in enumerate(value)
                    ]
                )
            else:
                return tuple(value)
        elif origin is tuple and _safe_isinstance(value, (list, tuple)):
            if args and ... in args:
                return tuple(
                    [
                        _coerce(v, args[0], custom_handlers, f"{key}.{i}")
                        for i, v in enumerate(value)
                    ]
                )
            elif args:
                return tuple(
                    [
                        _coerce(v, arg, custom_handlers, f"{key}.{i}")
                        for i, (v, arg) in enumerate(zip(value, args))
                    ]
                )
            else:
                return tuple(value)
        elif (
            origin is dict
            or origin is collections.abc.Mapping
            or origin is collections.abc.MutableMapping
        ) and _safe_isinstance(value, dict):
            if args:
                return {
                    _coerce(k, args[0], custom_handlers, f"{key}.{k}"): _coerce(
                        v, args[1], custom_handlers, f"{key}.{k}"
                    )
                    for k, v in value.items()
                }
            else:
                return value
        elif origin is typing.Literal and args and value in args:
            return value
        elif (
            dataclasses.is_dataclass(allowed_type)
            # e.g. TypedDict
            or _safe_issubclass(allowed_type, dict)
        ) and _safe_isinstance(value, dict):
            if _safe_issubclass(allowed_type, Registrable):
                type_name = value.get("type", allowed_type._default_type)
                if type_name is not None:
                    allowed_type = allowed_type.get_registered_class(type_name)
            type_hints = typing.get_type_hints(allowed_type)
            kwargs = {}
            for k, v in value.items():
                try:
                    type_hint = type_hints[k]
                except KeyError as e:
                    raise KeyError(
                        f"type {allowed_type} has no field '{k}' (full key '{key}.{k}')"
                    ) from e
                kwargs[k] = _coerce(v, type_hint, custom_handlers, f"{key}.{k}")
            return allowed_type(**kwargs)

    if Any in allowed_types:
        return value

    raise TypeError(
        f"Not sure how to coerce value {value} at key '{key}' to any "
        f"of {allowed_types} from type hint '{type_hint}'"
    )
