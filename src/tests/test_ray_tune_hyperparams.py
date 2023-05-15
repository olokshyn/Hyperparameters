import pytest
from pytest import approx
from ray import tune

from hyperparameters import HP, Hyperparams
from hyperparameters.ray_tune_hyperparams import RayTuneHyperparamsMixin


@pytest.fixture
def params() -> RayTuneHyperparamsMixin:
    class TestHyperparams(Hyperparams, RayTuneHyperparamsMixin):
        field1: int = HP(
            "Field1 description",
            default=13,
            search_space=tune.randint(3, 33),
        )
        field2: float = HP(
            "Field2 description",
            default=0.33,
            search_space=tune.loguniform(1e-5, 1e-2),
        )
        field3: int = HP(
            "Field3 description",
            default=5,
            tunable=True,
            choices=[1, 3, 5, 7, 9, 11, 13],
        )
        field4: bool = HP(
            "Field4 description",
            default=True,
            tunable=True,
        )
        field5: str = HP(
            "Field5 description",
            tunable=True,
            choices=["up", "right", "down", "left"],
        )
        field6: str = HP(
            "Field6 description",
            tunable=True,
            default="empty",
        )

    return TestHyperparams(
        field1=15,
        field3=7,
        field5="up",
        field6="full",
    )


def test_ray_tune_hyperparams(
    params: RayTuneHyperparamsMixin,
) -> None:
    def assert_equal(actual, expected):
        if actual == expected:
            return
        assert actual.__class__ is expected.__class__
        assert actual.__dict__.keys() == expected.__dict__.keys()
        for k in actual.__dict__:
            assert_equal(actual.__dict__[k], expected.__dict__[k])

    actual = params.ray_tune_param_space(use_current_values=False)
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

    actual = params.ray_tune_param_space(use_current_values=True)
    expected = {
        "field1": tune.randint(3, 33),
        "field2": tune.loguniform(1e-5, 1e-2),
        "field3": tune.choice([1, 3, 5, 7, 9, 11, 13]),
        "field4": tune.choice([False, True]),
        "field5": tune.choice(["up", "right", "down", "left"]),
        "field6": "full",
    }
    assert actual.keys() == expected.keys()
    for key in actual:
        assert_equal(actual[key], expected[key])


def test_ray_tune_best_value(
    params: RayTuneHyperparamsMixin,
) -> None:
    best_values = params.ray_tune_best_values(use_current_values=False)
    assert best_values == {
        "field1": 13,
        "field2": approx(0.33),
        "field3": 5,
        "field4": True,
        "field6": "empty",
    }

    best_values = params.ray_tune_best_values(use_current_values=True)
    assert best_values == {
        "field1": 15,
        "field2": approx(0.33),
        "field3": 7,
        "field4": True,
        "field5": "up",
        "field6": "full",
    }
