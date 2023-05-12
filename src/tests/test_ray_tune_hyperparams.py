import pytest
from pytest import approx
from ray import tune

from hyperparameters import HP, Hyperparams
from hyperparameters.ray_tune_hyperparams import RayTuneHyperparamsMixin


@pytest.fixture
def test_hyperparams_cls() -> type[RayTuneHyperparamsMixin]:
    class TestHyperparams(Hyperparams, RayTuneHyperparamsMixin):
        field1: int = HP(
            description="Field1 description",
            default=13,
            search_space=tune.randint(3, 33),
        )
        field2: float = HP(
            description="Field2 description",
            default=0.33,
            search_space=tune.loguniform(1e-5, 1e-2),
        )
        field3: int = HP(
            description="Field3 description",
            default=5,
            tunable=True,
            choices=[1, 3, 5, 7, 9, 11, 13],
        )
        field4: bool = HP(
            description="Field4 description",
            default=True,
            tunable=True,
        )
        field5: str = HP(
            description="Field5 description",
            tunable=True,
            choices=["up", "right", "down", "left"],
        )
        field6: str = HP(
            description="Field6 description",
            tunable=True,
            default="empty",
        )

    return TestHyperparams


def test_ray_tune_hyperparams(
    test_hyperparams_cls: type[RayTuneHyperparamsMixin],
) -> None:
    def assert_equal(actual, expected):
        if actual == expected:
            return
        assert actual.__class__ is expected.__class__
        assert actual.__dict__.keys() == expected.__dict__.keys()
        for k in actual.__dict__:
            assert_equal(actual.__dict__[k], expected.__dict__[k])

    actual = test_hyperparams_cls.ray_tune_param_space()
    expected = {
        "field1": tune.randint(3, 33),
        "field2": tune.loguniform(1e-5, 1e-2),
        "field3": tune.choice([1, 3, 5, 7, 9, 11, 13]),
        "field4": tune.choice([False, True]),
        "field5": tune.choice(["up", "right", "down", "left"]),
        "field6": "empty",
    }
    assert actual.keys() == expected.keys()
    for key in actual:
        assert_equal(actual[key], expected[key])


def test_ray_tune_best_value(
    test_hyperparams_cls: type[RayTuneHyperparamsMixin],
) -> None:
    best_values = test_hyperparams_cls.ray_tune_best_values()
    assert best_values == {
        "field1": 13,
        "field2": approx(0.33),
        "field3": 5,
        "field4": True,
        "field6": "empty",
    }
