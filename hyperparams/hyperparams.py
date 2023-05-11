import argparse
from functools import partial, wraps
from typing import Any, Iterator, TypeVar, Protocol, _ProtocolMeta

from pydantic.fields import Field, Undefined, Validator
from pydantic.main import BaseModel, ModelField, ModelMetaclass


class HyperparamInfo(BaseModel):
    class Config:
        validation = False
        arbitrary_types_allowed = True

    tunable: bool = False
    search_space: Any = None
    default: Any = None
    choices: list[Any] | None = None


def Hyperparam(
    *,
    description: str,
    default: Any = Undefined,
    tunable: bool | None = None,
    search_space: Any = None,
    choices: list[Any] | None = None,
):
    field = Field(
        default=default,
        description=description,
    )
    default = default if default is not Undefined else None
    field.extra["info"] = HyperparamInfo(
        tunable=tunable if tunable is not None else search_space is not None,
        search_space=search_space,
        default=default,
        choices=choices,
    )
    return field


def _choices_validator(value: Any, *, field_name: str, choices: list[Any]) -> None:
    if value not in choices:
        raise ValueError(
            f"Param {field_name} is {value} but must be one of [{', '.join(choices)}]"
        )
    return value


class HyperparamsMeta(ModelMetaclass, _ProtocolMeta):
    def __new__(mcs, name, bases, namespace, **kwargs) -> type[BaseModel]:
        cls: type[BaseModel] = super().__new__(mcs, name, bases, namespace, **kwargs)
        field: ModelField
        for field_name, field in cls.__fields__.items():
            if field.default is not None and not isinstance(field.default, field.type_):
                raise TypeError(
                    f"Field {field_name} is of type {field.type_} but has "
                    f"default value '{field.default}' of type {type(field.default)}"
                )

            info: HyperparamInfo | None = field.field_info.extra.get("info")
            assert info is None or isinstance(info, HyperparamInfo)
            if field.type_ is bool and info is not None:
                if info.choices is not None:
                    raise ValueError(
                        f"Field {field_name} is bool and cannot have choices set"
                    )
                info.choices = [False, True]
            if info is not None and info.choices is not None:
                for choice in info.choices:
                    if not isinstance(choice, field.type_):
                        raise TypeError(
                            f"Field {field_name} is of type {field.type_} but contains "
                            f"choice '{choice}' of type {type(choice)}"
                        )
                if field.default is not None and field.default not in info.choices:
                    raise ValueError(
                        f"Field {field_name} has invalid default '{field.default}' "
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
        validate_assignment = True
        arbitrary_types_allowed = True

    @classmethod
    def add_arguments(
        cls: type[SelfHyperparams], parser: argparse.ArgumentParser
    ) -> None:
        for field_name, field in cls.__fields__.items():
            info: HyperparamInfo | None = field.field_info.extra.get("info")
            assert info is None or isinstance(info, HyperparamInfo)
            option_name = "--" + field_name.replace("_", "-")
            help = field.field_info.description
            required = field.required is True or field.default is None

            if field.type_ is bool:
                group = parser.add_mutually_exclusive_group(required=required)
                group.add_argument(
                    option_name,
                    action="store_true",
                    dest=field_name,
                    help=help,
                )
                group.add_argument(
                    "--no-" + field_name.replace("_", "-"),
                    action="store_false",
                    dest=field_name,
                    help="Disable: " + help,
                )
                if field.default is not None:
                    parser.set_defaults(**{field_name: bool(field.default)})
            else:
                parser.add_argument(
                    option_name,
                    help=help,
                    type=field.type_,
                    default=field.default,
                    required=required,
                    choices=getattr(info, "choices", None),
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
            info: HyperparamInfo | None = field.field_info.extra.get("info")
            assert info is None or isinstance(info, HyperparamInfo)
            if info is not None and info.tunable:
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
