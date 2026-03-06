from __future__ import annotations

import collections.abc
import dataclasses
import inspect
import types
import typing
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Type, TypeVar

import typing_extensions

from .registrable import Registrable
from .types import *

C = TypeVar("C", bound=Dataclass)


class DecodeError(TypeError):
    def __init__(self, *args, inner_failures: list[str] | None = None):
        super().__init__(*args)
        self.inner_failures = inner_failures or []


class Decoder:
    custom_handlers: ClassVar[dict[Any, Callable[[Any], Any]]] = {}

    def register_decoder(self, encoder_fun: Callable[[Any], Any], *target_types: Any):
        for type in target_types:
            self.custom_handlers[type] = encoder_fun

    def __call__(self, config_class: Type[C], data: dict[str, Any]) -> C:
        """
        Decode a dataset from a JSON-safe dictionary. The inverse of :func:`encode()`.

        .. warning::
            This may execute arbitrary code contained in annotations.

        :raises DecodeError: If decoding fails.
        """
        if _safe_issubclass(config_class, Registrable):
            type_name = data.pop("type", config_class._default_type)  # type: ignore[attr-defined]
            if type_name is not None and type_name != config_class.registered_name:  # type: ignore[attr-defined]
                config_class = config_class.get_registered_class(type_name)  # type: ignore[attr-defined]

        type_hints = _get_type_hints(config_class)
        kwargs: dict[str, Any] = {}
        for k, v in data.items():
            if k not in type_hints:
                raise DecodeError(f"class '{config_class.__qualname__}' has no attribute '{k}'")
            kwargs[k] = _coerce(v, type_hints[k], self.custom_handlers, k, config_class)

        try:
            return config_class(**kwargs)
        except TypeError as exc:
            raise DecodeError(f"Failed to decode {config_class.__qualname__}, {exc}.") from exc


decode = Decoder()


def _get_type_hints(obj: Any) -> dict[str, Any]:
    try:
        return typing.get_type_hints(obj)
    except NameError as e:
        raise NameError(
            f"{str(e)}. If you're using 'from __future__ import annotations' you may need to import "
            "this type or ensure it's defined globally."
        ) from e


def _resolve_type_hint(type_hint: Any, owner: Any) -> Any:
    if isinstance(type_hint, str):
        if not hasattr(typing_extensions, "evaluate_forward_ref"):
            raise ImportError(
                "evaluating string type hints (like forward references) "
                "requires a newer version of typing extensions"
            )
        type_hint = typing_extensions.evaluate_forward_ref(  # type: ignore
            typing.ForwardRef(type_hint), owner=owner
        )
    # NOTE: In Python 3.11+ typing_extensions.Self should just be a re-export of typing.Self,
    # so we're being extra defensive here.
    elif type_hint is typing_extensions.Self or (hasattr(typing, "Self") and type_hint is getattr(typing, "Self")):  # type: ignore
        if inspect.isclass(owner):
            type_hint = owner
        else:
            type_hint = type(owner)
    return type_hint


def _get_allowed_types(type_hint: Any) -> tuple[Any, ...]:
    # NOTE: 'types.UnionType' doesn't cover union types with 'typing.*' types.
    if _safe_isinstance(type_hint, (types.UnionType, type(typing.List | None))):
        return typing.get_args(type_hint)
    elif _safe_isinstance(type_hint, dataclasses.InitVar):
        return _get_allowed_types(type_hint.type)
    # TypeAliasType added in 3.12
    elif hasattr(typing, "TypeAliasType") and _safe_isinstance(type_hint, typing.TypeAliasType):  # type: ignore
        return _get_allowed_types(type_hint.__value__)
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
    value: Any,
    type_hint: Any,
    custom_handlers: dict[Any, Callable[[Any], Any]],
    key: str,
    owner: Any,
) -> Any:
    if value is MISSING:
        raise ValueError(f"Missing required field at '{key}'")

    type_hint = _resolve_type_hint(type_hint, owner)

    if type_hint in custom_handlers:
        return custom_handlers[type_hint](value)

    allowed_types = tuple(_resolve_type_hint(t, owner) for t in _get_allowed_types(type_hint))
    failures: list[str] = []
    for allowed_type in allowed_types:
        try:
            if allowed_type in custom_handlers:
                return custom_handlers[allowed_type](value)

            if _safe_isinstance(value, allowed_type):
                return value

            if _safe_issubclass(allowed_type, Enum):
                return allowed_type(value)

            # e.g. typing.NamedTuple
            if _safe_issubclass(allowed_type, tuple) and _safe_isinstance(value, (list, tuple)):
                return allowed_type(*value)

            if _safe_issubclass(allowed_type, datetime) and _safe_isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)

            if allowed_type is float:
                if _safe_isinstance(value, (float, int)):
                    return float(value)
                elif _safe_isinstance(value, str):  # need this to handle scientific notation
                    return float(value)

            if allowed_type is int:
                if _safe_isinstance(value, (int, float)) and (value_as_int := int(value)) == value:
                    return value_as_int
                elif _safe_isinstance(value, str):
                    value_as_float = float(value)
                    if (value_as_int := int(value_as_float)) == value_as_float:
                        return value_as_int

            origin = typing.get_origin(allowed_type)
            args = typing.get_args(allowed_type)
            if (origin is list or origin is collections.abc.MutableSequence) and _safe_isinstance(
                value, (list, tuple)
            ):
                if args:
                    return [
                        _coerce(v, args[0], custom_handlers, f"{key}.{i}", owner)
                        for i, v in enumerate(value)
                    ]
                else:
                    return list(value)
            elif (
                origin is set
                or origin is collections.abc.Set
                or origin is collections.abc.MutableSet
            ) and _safe_isinstance(value, (list, tuple, set)):
                if args:
                    return set(
                        _coerce(v, args[0], custom_handlers, f"{key}.{i}", owner)
                        for i, v in enumerate(value)
                    )
                else:
                    return set(value)
            elif origin is collections.abc.Sequence and _safe_isinstance(value, (list, tuple)):
                if args:
                    return tuple(
                        [
                            _coerce(v, args[0], custom_handlers, f"{key}.{i}", owner)
                            for i, v in enumerate(value)
                        ]
                    )
                else:
                    return tuple(value)
            elif origin is tuple and _safe_isinstance(value, (list, tuple)):
                if args and ... in args:
                    return tuple(
                        [
                            _coerce(v, args[0], custom_handlers, f"{key}.{i}", owner)
                            for i, v in enumerate(value)
                        ]
                    )
                elif args:
                    return tuple(
                        [
                            _coerce(v, arg, custom_handlers, f"{key}.{i}", owner)
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
                        _coerce(k, args[0], custom_handlers, f"{key}.{k}", owner): _coerce(
                            v, args[1], custom_handlers, f"{key}.{k}", owner
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
                    if type_name is not None and type_name != allowed_type.registered_name:
                        allowed_type = allowed_type.get_registered_class(type_name)

                type_hints = _get_type_hints(allowed_type)

                kwargs = {}
                for k, v in value.items():
                    if k not in type_hints:
                        raise AttributeError(
                            f"class '{allowed_type.__qualname__}' has no attribute '{k}'"
                        )
                    type_hint_ = type_hints[k]
                    kwargs[k] = _coerce(v, type_hint_, custom_handlers, f"{key}.{k}", allowed_type)
                return allowed_type(**kwargs)
        except (TypeError, ValueError, AttributeError) as exc:
            if isinstance(exc, DecodeError):
                failures.extend(exc.inner_failures)
            else:
                failures.append(
                    f"[{key}] coercing to {allowed_type} failed with {type(exc).__name__}: {exc}"
                )

    if Any in allowed_types:
        return value

    error_message: str
    if len(allowed_types) > 1:
        error_message = (
            f"Failed to coerce value {value} at key '{key}' to any "
            f"of {', '.join([str(t) for t in allowed_types])} from type hint '{type_hint}' ({type(type_hint)})."
        )
    else:
        error_message = (
            f"Failed to coerce value {value} at key '{key}' to a "
            f"{allowed_types[0]} from type hint '{type_hint}' ({type(type_hint)})."
        )

    for failure in failures:
        error_message += f"\n→ {failure}"

    raise DecodeError(error_message, inner_failures=failures)
