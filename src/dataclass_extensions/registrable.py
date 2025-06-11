from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass
from typing import Callable, ClassVar, Type, TypeVar

R = TypeVar("R", bound="Registrable")


@dataclass
class Registrable:
    _registry: ClassVar[dict[str, Type[Registrable]]]
    _default_type: ClassVar[str | None]

    type: dataclasses.InitVar[str | None] = dataclasses.field(
        default=None, kw_only=True, repr=False
    )

    def __new__(cls, *args, type: str | None = None, **kwargs):
        del args, kwargs
        if type is not None and (
            not hasattr(cls, "registered_name") or type != cls.registered_name  # type: ignore
        ):
            if type not in cls._registry:
                raise KeyError(
                    f"'{type}' is not registered name for {cls.__name__}. "
                    f"Available choices are: {list(cls._registry.keys())}"
                )
            return super().__new__(cls._registry[type])
        elif cls._default_type is not None and not hasattr(cls, "registered_name"):
            return super().__new__(cls._registry[cls._default_type])
        else:
            return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "_registry"):
            cls._registry = {}
        if not hasattr(cls, "_default_type"):
            cls._default_type = None

    @classmethod
    def register(cls, name: str, default: bool = False) -> Callable[[Type[R]], Type[R]]:
        def register_subclass(subclass: Type[R]) -> Type[R]:
            if not issubclass(subclass, cls):
                raise TypeError(
                    f"class {subclass.__name__} must be a subclass of {cls.__name__} in order to register it"
                )
            if not dataclasses.is_dataclass(subclass):
                raise TypeError(
                    f"class {subclass.__name__} must be a dataclass in order to register it"
                )
            if default:
                if cls._default_type is not None:
                    raise ValueError(
                        f"A default implementation for {cls.__name__} has already been registered"
                    )
                else:
                    cls._default_type = name

            fields = [
                (f.name, f.type, f) for f in dataclasses.fields(subclass) if f.name != "type"  # type: ignore
            ] + [
                ("registered_name", ClassVar[str], name),  # type: ignore
                ("registered_base", ClassVar[R], cls),  # type: ignore
                ("type", dataclasses.InitVar[str | None], dataclasses.field(default=name, kw_only=True, repr=False)),  # type: ignore
            ]
            subclass = dataclasses.make_dataclass(
                subclass.__name__,
                fields,  # type: ignore
                bases=(subclass,),
            )
            cls._registry[name] = subclass
            return subclass

        return register_subclass

    @classmethod
    def get_registered_name(cls: Type[R], subclass: Type[R] | None = None) -> str:
        if subclass is None:
            if hasattr(cls, "registered_name"):
                return cls.registered_name  # type: ignore
            else:
                raise ValueError(
                    f"class {cls.__name__} is not a registered subclass of any base registrable class"
                )

        for name, registered_subclass in cls._registry.items():
            if registered_subclass == subclass:
                return name

        raise ValueError(
            f"class {subclass.__name__} is not a registered subclass of {cls.__name__}"
        )

    @classmethod
    def get_registered_class(cls: Type[R], type: str) -> Type[R]:
        if type not in cls._registry:
            raise KeyError(
                f"'{type}' is not registered name for {cls.__name__}. "
                f"Available choices are: {cls.get_registered_names()}"
            )
        return typing.cast(Type[R], cls._registry[type])

    @classmethod
    def get_registered_names(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_default(cls: Type[R]) -> Type[R]:
        if cls._default_type is None:
            raise ValueError(f"A default implementation of {cls.__name__} has not been registered")
        return cls.get_registered_class(cls._default_type)
