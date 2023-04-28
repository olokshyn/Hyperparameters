import argparse

from ray import tune

from hyperparams import Hyperparams, HP
from hyperparams.ray_tune_hyperparams import RayTuneHyperparamsMixin


class MyTest(Hyperparams, RayTuneHyperparamsMixin):
    lr: float = HP(
        description="Learning Rate",
        default=0.1,
        search_space=tune.loguniform(1e-2, 1e4),
    )
    epochs: int = HP(description="Number of epochs", default=7)
    mode: str = HP(
        description="Training mode",
        default="backprop",
        choices=["backprop", "sazil", "custom"],
    )
    do_train: bool = HP(
        description="Whether should train the model",
    )
    delete_model: bool = HP(
        description="Delete the model after training",
        default=False,
    )


def main():
    parser = argparse.ArgumentParser()
    MyTest.add_arguments(parser)
    args = parser.parse_args()
    p1 = MyTest.from_arguments(args)
    p2 = MyTest.from_arguments(args, lr=0.8, mode="sazil")
    print(p1.json())
    print(p2.json(indent=0))
    param_space = p1.ray_tune_param_space()
    print(p1.diff(p2))


if __name__ == "__main__":
    main()
