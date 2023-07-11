import argparse
import os
from functools import partial, wraps
from typing import Any, Iterator, Optional, Protocol, TypeVar, _ProtocolMeta

from pydantic.fields import Field, Undefined, Validator
from pydantic.main import BaseModel, ModelField, ModelMetaclass


class HyperparamInfo(BaseModel):
    class Config:
        validation = False
        arbitrary_types_allowed = True

    description: str
    default: Any = None
    tunable: bool = False
    search_space: Any = None
    choices: list[Any] | None = None
    adjust_relative_path: bool = False

    annotation: Any = None
    type_: Any = None
    required: bool = False

    def can_be_none(self) -> bool:
        if self.annotation is Any:
            return True
        return getattr(self.annotation, "_name", None) == "Optional"


def HP(
    description: str,
    *,
    default: Any = Undefined,
    tunable: bool | None = None,
    search_space: Any = None,
    choices: list[Any] | None = None,
    adjust_relative_path: bool = False,
):
    field = Field(
        default=default,
        description=description,
    )
    field.extra["info"] = HyperparamInfo(
        description=description,
        default=default if default is not Undefined else None,
        tunable=tunable if tunable is not None else search_space is not None,
        search_space=search_space,
        choices=choices,
        adjust_relative_path=adjust_relative_path,
    )
    return field


def _choices_validator(value: Any, *, field_name: str, choices: list[Any]) -> None:
    if value not in choices:
        raise ValueError(
            f"Param {field_name} is {value} but must be one of [{', '.join(choices)}]"
        )
    return value


def _load_info(field_name: str, field: ModelField) -> HyperparamInfo:
    info: HyperparamInfo | None = field.field_info.extra.get("info")
    if info is None:
        raise ValueError(f"Field {field_name} was not defined correctly, use HP().")
    assert isinstance(info, HyperparamInfo)
    return info


def _get_config_value(cls: type, name: str, default: Any) -> Any:
    for curr_cls in cls.__mro__:
        config = getattr(curr_cls, "Config", None)
        if config is None:
            continue
        if hasattr(config, name):
            return getattr(config, name)
    return default


def _get_relative_paths_root(cls: type) -> Optional[str]:
    return _get_config_value(cls, "relative_paths_root", None)


class HyperparamsMeta(ModelMetaclass, _ProtocolMeta):
    def __new__(mcs, name, bases, namespace, **kwargs) -> type[BaseModel]:
        cls: type[BaseModel] = super().__new__(mcs, name, bases, namespace, **kwargs)
        relative_paths_root = _get_relative_paths_root(cls)
        field: ModelField
        for field_name, field in cls.__fields__.items():
            info = _load_info(field_name, field)

            info.type_ = field.type_
            info.annotation = field.annotation
            info.required = field.required is True

            if (
                relative_paths_root
                and info.adjust_relative_path
                and info.default is not None
                and not os.path.isabs(info.default)
            ):
                value = os.path.join(relative_paths_root, info.default)
                info.default = value
                field.default = value

            if not info.required:
                if info.default is None and not info.can_be_none():
                    raise ValueError(
                        f"Field {field_name} is of type {info.annotation} but is None by default. Use Optional."
                    )

                if info.default is not None and not isinstance(
                    info.default, info.type_
                ):
                    raise ValueError(
                        f"Field {field_name} is of type {info.annotation} but has "
                        f"default value '{info.default}' of type {type(info.default)}"
                    )

            if info.type_ is bool:
                if info.choices is not None and info.choices != [False, True]:
                    raise ValueError(
                        f"Field {field_name} is bool and cannot have choices set. "
                        "False and True are the only possible choices."
                    )
                info.choices = [False, True]
            if info.choices is not None:
                for choice in info.choices:
                    if not isinstance(choice, info.type_):
                        raise ValueError(
                            f"Field {field_name} is of type {info.annotation} but contains "
                            f"choice '{choice}' of type {type(choice)}"
                        )
                if not info.required and info.default not in info.choices:
                    raise ValueError(
                        f"Field {field_name} has invalid default '{info.default}' "
                        "that is not one of the choices"
                    )

                validator = Validator(
                    func=partial(
                        _choices_validator, field_name=field_name, choices=info.choices
                    ),
                    always=True,
                    check_fields=True,
                )
                field.class_validators[field_name] = validator
                field.populate_validators()
                # Note: cls.__validators__ is a dict[str, list[Callable]]
                cls.__validators__.setdefault(field_name, []).append(validator)  # type: ignore
        return cls


SelfHyperparamsProtocol = TypeVar(
    "SelfHyperparamsProtocol", bound="HyperparamsProtocol"
)


class HyperparamsProtocol(Protocol):
    @classmethod
    def parameters(cls: type[SelfHyperparamsProtocol]) -> dict[str, HyperparamInfo]:
        ...

    @classmethod
    def add_arguments(
        cls: type[SelfHyperparamsProtocol], parser: argparse.ArgumentParser
    ) -> None:
        ...

    @classmethod
    def from_arguments(
        cls: type[SelfHyperparamsProtocol],
        args: argparse.Namespace,
        **overrides,
    ) -> SelfHyperparamsProtocol:
        ...

    @classmethod
    def _tunable_params(cls) -> Iterator[tuple[str, HyperparamInfo]]:
        ...


SelfHyperparams = TypeVar("SelfHyperparams", bound="Hyperparams")


class Hyperparams(BaseModel, HyperparamsProtocol, metaclass=HyperparamsMeta):
    class Config:
        # BaseModel configs
        validate_assignment = True
        arbitrary_types_allowed = True

        # Hyperparams config
        relative_paths_root: str = os.getcwd()

    def __init__(self, **data: Any) -> None:
        relative_paths_root = _get_relative_paths_root(self.__class__)
        if relative_paths_root:
            for name in data:
                if name not in self.__fields__:
                    continue
                info: HyperparamInfo = _load_info(name, self.__fields__[name])
                if info.adjust_relative_path and not os.path.isabs(data[name]):
                    data[name] = os.path.join(relative_paths_root, data[name])
        super().__init__(**data)

    def __setattr__(self, name, value) -> None:
        relative_paths_root = _get_relative_paths_root(self.__class__)
        if relative_paths_root:
            info: HyperparamInfo = _load_info(name, self.__fields__[name])
            if info.adjust_relative_path and not os.path.isabs(value):
                value = os.path.join(relative_paths_root, value)
        return super().__setattr__(name, value)

    @classmethod
    def parameters(cls: type[SelfHyperparams]) -> dict[str, HyperparamInfo]:
        return {
            field_name: _load_info(field_name, field)
            for field_name, field in cls.__fields__.items()
        }

    # TODO: add nargs support
    @classmethod
    def add_arguments(
        cls: type[SelfHyperparams], parser: argparse.ArgumentParser
    ) -> None:
        for field_name, field in cls.__fields__.items():
            info = _load_info(field_name, field)
            option_name = "--" + field_name.replace("_", "-")

            if info.type_ is bool:
                group = parser.add_mutually_exclusive_group(required=info.required)
                group.add_argument(
                    option_name,
                    action="store_true",
                    dest=field_name,
                    help=info.description,
                )
                group.add_argument(
                    "--no-" + field_name.replace("_", "-"),
                    action="store_false",
                    dest=field_name,
                    help="Disable: " + info.description,
                )
                if info.default is not None:
                    parser.set_defaults(**{field_name: bool(info.default)})
            else:
                parser.add_argument(
                    option_name,
                    help=info.description,
                    type=info.type_,
                    default=info.default,
                    required=info.required,
                    choices=info.choices,
                )

    @classmethod
    def from_arguments(
        cls: type[SelfHyperparams],
        args: argparse.Namespace,
        **overrides,
    ) -> SelfHyperparams:
        fields = {
            **{f: args.__dict__[f] for f in cls.__fields__},
            **overrides,
        }
        return cls(**fields)

    @classmethod
    def _tunable_params(cls) -> Iterator[tuple[str, HyperparamInfo]]:
        for field_name, field in cls.__fields__.items():
            info = _load_info(field_name, field)
            if info.tunable:
                if (
                    info.search_space is None
                    and info.choices is None
                    and info.default is None
                ):
                    raise ValueError(
                        f"Tunable parameter {field_name} must have "
                        "a search space or a default value specified"
                    )
                yield field_name, info

    @wraps(BaseModel.json)
    def json(self, **kwargs) -> str:
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        elif kwargs["indent"] == 0:
            del kwargs["indent"]
        return super().json(**kwargs)

    def diff(self: SelfHyperparams, other: SelfHyperparams) -> dict:
        my_dict = self.dict()
        other_dict = other.dict()
        all_keys = set(my_dict) | set(other_dict)
        return {
            k: (my_dict.get(k), other_dict.get(k))
            for k in all_keys
            if my_dict.get(k) != other_dict.get(k)
        }

    def update(
        self: SelfHyperparams,
        data: dict[str, Any],
        *,
        inplace: bool = False,
        validate: bool = False,
    ) -> SelfHyperparams:
        if validate:
            unknown_keys = data.keys() - self.__dict__.keys()
            if unknown_keys:
                raise ValueError(
                    f"Update data contains unknown keys: {' '.join(unknown_keys)}"
                )
            target = self
            if not inplace:
                target = self.copy()
            for name in data:
                if name in target.__dict__:
                    setattr(target, name, data[name])
            return target
        else:
            if inplace:
                self.__dict__.update(data)
                return self
            else:
                return self.copy(update=data)
