import argparse
from functools import partial, wraps
from typing import Any, TypeVar

from pydantic import validator
from pydantic.fields import Field, Undefined, UndefinedType, Validator
from pydantic.main import BaseModel, ModelMetaclass


def Hyperparam(
    *,
    description: str,
    default: Any = Undefined,
    choices: list[Any] | UndefinedType = Undefined,
):
    field = Field(
        default=default,
        description=description,
    )
    if choices is not Undefined:
        field.extra.setdefault("choices", choices)
    return field


def _choices_validator(value: Any, *, field_name: str, choices: list[Any]) -> None:
    if value not in choices:
        raise ValueError(
            f"Param {field_name} is {value} but must be one of [{', '.join(choices)}]"
        )
    return value


SelfHyperparams = TypeVar("SelfHyperparams", bound="Hyperparams")


class HyperparamsMeta(ModelMetaclass):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        for field_name, field in cls.__fields__.items():
            choices = field.field_info.extra.get("choices")
            if choices is not None:
                validator = Validator(
                    func=partial(
                        _choices_validator, field_name=field_name, choices=choices
                    ),
                    always=True,
                    check_fields=True,
                )
                field.class_validators[field_name] = validator
                field.populate_validators()
                cls.__validators__.setdefault(field_name, []).append(validator)
        return cls


class Hyperparams(BaseModel, metaclass=HyperparamsMeta):
    class Config:
        validate_assignment = True

    @classmethod
    def add_arguments(
        cls: type[SelfHyperparams], parser: argparse.ArgumentParser
    ) -> None:
        for field_name, field in cls.__fields__.items():
            choices = field.field_info.extra.get("choices")
            parser.add_argument(
                "--" + field_name.replace("_", "-"),
                type=field.type_,
                default=field.default,
                help=field.field_info.description,
                required=field.required if isinstance(field.required, bool) else False,
                choices=choices,
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


class MyTest(Hyperparams):
    lr: float = Hyperparam(description="Learning Rate", default=0.1)
    epochs: int = Hyperparam(description="Number of epochs", default=7)
    mode: str = Hyperparam(
        description="Training mode",
        default="backprop",
        choices=["backprop", "sazil", "custom"],
    )

    @validator("epochs")
    def validate_epochs(cls, v):
        if v > 10:
            raise ValueError(f"Epochs {v} is too big!")
        return v


def main():
    parser = argparse.ArgumentParser()
    MyTest.add_arguments(parser)
    args = parser.parse_args()
    p1 = MyTest.from_arguments(args)
    p2 = MyTest.from_arguments(args, lr=0.8, mode="sazil")
    print(p1.json())
    print(p2.json(indent=0))
    p2.mode = "test"
    p2.epochs = 20
    print(p1.diff(p2))


if __name__ == "__main__":
    main()
