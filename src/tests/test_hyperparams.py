import argparse

from pydantic import ValidationError
from pytest import approx

from hyperparameters import HP, Hyperparams
from hyperparameters.hyperparams import HyperparamInfo


def test_argparse_basic_fields() -> None:
    class TestHyperparams(Hyperparams):
        field1: int = HP(
            description="Field1 description",
            default=10,
        )
        field2: float = HP(
            description="Field2 description",
            default=0.7,
        )
        field3: str = HP(
            description="Field3 description",
            default="basic value",
        )
        field4: str = HP(
            description="Required field",
        )

    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument("--other", type=int, help="Some other argument")
    TestHyperparams.add_arguments(parser)

    # Check parser state
    o0 = parser._actions[1]
    assert o0.dest == "other"
    assert o0.option_strings == ["--other"]
    assert o0.type == int
    assert o0.help == "Some other argument"
    assert o0.default is None
    assert o0.required is False

    f1 = parser._actions[2]
    assert f1.dest == "field1"
    assert f1.option_strings == ["--field1"]
    assert f1.type == int
    assert f1.help == "Field1 description"
    assert f1.default == 10
    assert f1.required is False

    f2 = parser._actions[3]
    assert f2.dest == "field2"
    assert f2.option_strings == ["--field2"]
    assert f2.type == float
    assert f2.help == "Field2 description"
    assert f2.default == approx(0.7)
    assert f2.required is False

    f3 = parser._actions[4]
    assert f3.dest == "field3"
    assert f3.option_strings == ["--field3"]
    assert f3.type == str
    assert f3.help == "Field3 description"
    assert f3.default == "basic value"
    assert f3.required is False

    f4 = parser._actions[5]
    assert f4.dest == "field4"
    assert f4.option_strings == ["--field4"]
    assert f4.type == str
    assert f4.help == "Required field"
    assert f4.default is None
    assert f4.required is True

    # Test required: field4
    try:
        parser.parse_args([])
        assert False
    except SystemExit as e:
        pass

    # Test default
    args = parser.parse_args(["--field4", "value"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == 10
    assert p.field2 == approx(0.7)
    assert p.field3 == "basic value"
    assert args.other is None

    # Violate field1 type constraints
    try:
        args = parser.parse_args(["--field1", "not an int", "--field4", "value"])
        assert False
    except argparse.ArgumentError as err:
        assert str(err) == "argument --field1: invalid int value: 'not an int'"

    # Violate field2 type constraints
    try:
        args = parser.parse_args(["--field2", "not a float", "--field4", "value"])
        assert False
    except argparse.ArgumentError as err:
        str(err) == "argument --field2: invalid float value: 'not a float'"

    # Pass valid values
    args = parser.parse_args(
        ["--field1", "5", "--field2", "0.3", "--field3", "hallo", "--field4", "Tschus"]
    )
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == 5
    assert p.field2 == approx(0.3)
    assert p.field3 == "hallo"
    assert p.field4 == "Tschus"


def test_argparse_basic_wrong_default() -> None:
    try:

        class TestHyperparams(Hyperparams):
            field: int = HP(
                description="Wrong default type",
                default=0.4,
            )

        assert False
    except TypeError as e:
        pass
    try:

        class TestHyperparams2(Hyperparams):
            field: str = HP(
                description="Wrong default type",
                default=4,
            )

        assert False
    except TypeError as e:
        pass


def test_argparse_bool_fields() -> None:
    class TestHyperparams(Hyperparams):
        field1: bool = HP(
            description="Field1 description",
            default=False,
        )
        field2: bool = HP(
            description="Field2 description",
            default=True,
        )
        field3: bool = HP(
            description="Required field",
        )

    parser = argparse.ArgumentParser(exit_on_error=False)
    TestHyperparams.add_arguments(parser)

    # Check parser state
    assert len(parser._mutually_exclusive_groups) == 3

    f1 = parser._actions[1]
    assert isinstance(f1, argparse._StoreTrueAction)
    assert f1.dest == "field1"
    assert f1.option_strings == ["--field1"]
    assert f1.type is None
    assert f1.help == "Field1 description"
    assert f1.default is False
    assert f1.required is False

    no_f1 = parser._actions[2]
    assert isinstance(no_f1, argparse._StoreFalseAction)
    assert no_f1.dest == "field1"
    assert no_f1.option_strings == ["--no-field1"]
    assert no_f1.type is None
    assert no_f1.help == "Disable: Field1 description"
    assert no_f1.default is False
    assert no_f1.required is False

    assert parser._defaults.get("field1") is False
    f1_group = parser._mutually_exclusive_groups[0]
    assert len(f1_group._group_actions) == 2
    assert f1_group._group_actions[0] == f1
    assert f1_group._group_actions[1] == no_f1

    f2 = parser._actions[3]
    assert isinstance(f2, argparse._StoreTrueAction)
    assert f2.dest == "field2"
    assert f2.option_strings == ["--field2"]
    assert f2.type is None
    assert f2.help == "Field2 description"
    assert f2.default is True
    assert f2.required is False

    no_f2 = parser._actions[4]
    assert isinstance(no_f2, argparse._StoreFalseAction)
    assert no_f2.dest == "field2"
    assert no_f2.option_strings == ["--no-field2"]
    assert no_f2.type is None
    assert no_f2.help == "Disable: Field2 description"
    assert no_f2.default is True
    assert no_f2.required is False

    assert parser._defaults.get("field2") is True
    f2_group = parser._mutually_exclusive_groups[1]
    assert len(f2_group._group_actions) == 2
    assert f2_group._group_actions[0] == f2
    assert f2_group._group_actions[1] == no_f2

    f3 = parser._actions[5]
    assert isinstance(f3, argparse._StoreTrueAction)
    assert f3.dest == "field3"
    assert f3.option_strings == ["--field3"]
    assert f3.type is None
    assert f3.help == "Required field"
    assert f3.default is False
    assert f3.required is False

    no_f3 = parser._actions[6]
    assert isinstance(no_f3, argparse._StoreFalseAction)
    assert no_f3.dest == "field3"
    assert no_f3.option_strings == ["--no-field3"]
    assert no_f3.type is None
    assert no_f3.help == "Disable: Required field"
    assert no_f3.default is True
    assert no_f3.required is False

    assert parser._defaults.get("field3") is None
    f3_group = parser._mutually_exclusive_groups[2]
    assert len(f3_group._group_actions) == 2
    assert f3_group._group_actions[0] == f3
    assert f3_group._group_actions[1] == no_f3

    # Test required: field3
    try:
        parser.parse_args([])
        assert False
    except SystemExit:
        pass

    # Test default
    args = parser.parse_args(["--field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is True
    assert p.field3 is True

    args = parser.parse_args(["--no-field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is True
    assert p.field3 is False

    # Test flags
    args = parser.parse_args(["--field1", "--field2", "--field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is True
    assert p.field2 is True
    assert p.field3 is True

    args = parser.parse_args(["--no-field1", "--field2", "--field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is True
    assert p.field3 is True

    args = parser.parse_args(["--field1", "--no-field2", "--field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is True
    assert p.field2 is False
    assert p.field3 is True

    args = parser.parse_args(["--no-field1", "--no-field2", "--field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is False
    assert p.field3 is True

    args = parser.parse_args(["--field1", "--field2", "--no-field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is True
    assert p.field2 is True
    assert p.field3 is False

    args = parser.parse_args(["--no-field1", "--field2", "--no-field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is True
    assert p.field3 is False

    args = parser.parse_args(["--field1", "--no-field2", "--no-field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is True
    assert p.field2 is False
    assert p.field3 is False

    args = parser.parse_args(["--no-field1", "--no-field2", "--no-field3"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 is False
    assert p.field2 is False
    assert p.field3 is False


def test_argparse_bool_conflict() -> None:
    class TestHyperparams(Hyperparams):
        field: bool = HP(
            description="A bool field",
        )

    parser = argparse.ArgumentParser()
    TestHyperparams.add_arguments(parser)
    try:
        parser.parse_args(["--field", "--no-field"])
        assert False
    except SystemExit as e:
        pass
    try:
        parser.parse_args(["--no-field", "--field"])
        assert False
    except SystemExit as e:
        pass


def test_argparse_choices_fields() -> None:
    class TestHyperparams(Hyperparams):
        field1: str = HP(
            description="Str choices",
            default="third",
            choices=["first", "second", "third", "fourth"],
        )
        field2: int = HP(
            description="Int choices",
            default=3,
            choices=[3, 5, 7],
        )
        field3: str = HP(
            description="Required choice",
            choices=["blue", "red"],
        )

    parser = argparse.ArgumentParser(exit_on_error=False)
    TestHyperparams.add_arguments(parser)

    # Check parser state
    f1 = parser._actions[1]
    assert f1.dest == "field1"
    assert f1.option_strings == ["--field1"]
    assert f1.type == str
    assert f1.help == "Str choices"
    assert f1.default == "third"
    assert f1.choices == ["first", "second", "third", "fourth"]
    assert f1.required is False

    f2 = parser._actions[2]
    assert f2.dest == "field2"
    assert f2.option_strings == ["--field2"]
    assert f2.type == int
    assert f2.help == "Int choices"
    assert f2.default == 3
    assert f2.choices == [3, 5, 7]
    assert f2.required is False

    f3 = parser._actions[3]
    assert f3.dest == "field3"
    assert f3.option_strings == ["--field3"]
    assert f3.type == str
    assert f3.help == "Required choice"
    assert f3.default is None
    assert f3.choices == ["blue", "red"]
    assert f3.required is True

    # Test required
    try:
        parser.parse_args([])
        assert False
    except SystemExit as e:
        pass

    # Test default
    args = parser.parse_args(["--field3", "blue"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == "third"
    assert p.field2 == 3
    assert p.field3 == "blue"

    # Test correct choices
    args = parser.parse_args(["--field1", "second", "--field2", "7", "--field3", "red"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == "second"
    assert p.field2 == 7
    assert p.field3 == "red"

    args = parser.parse_args(["--field1", "first", "--field2", "5", "--field3", "blue"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == "first"
    assert p.field2 == 5
    assert p.field3 == "blue"

    args = parser.parse_args(["--field1", "fourth", "--field2", "3", "--field3", "red"])
    p = TestHyperparams.from_arguments(args)
    assert p.field1 == "fourth"
    assert p.field2 == 3
    assert p.field3 == "red"

    # Test incorrect choices
    try:
        args = parser.parse_args(["--field1", "invalid", "--field3", "red"])
        assert False
    except argparse.ArgumentError as err:
        assert err.argument_name == "--field1"
    try:
        parser.parse_args(["--field2", "1", "--field3", "red"])
        assert False
    except argparse.ArgumentError as err:
        assert err.argument_name == "--field2"


def test_argparse_choices_invalid_type() -> None:
    try:

        class TestHyperparams(Hyperparams):
            field: int = HP(
                description="Int field with str choices",
                default=5,
                choices=["1", "3", "5"],
            )

        assert False
    except TypeError as e:
        pass


def test_argparse_choices_wrong_default() -> None:
    try:

        class TestHyperparams(Hyperparams):
            field: str = HP(
                description="Default value is not in choices",
                default="first",
                choices=["second", "third", "fourth"],
            )

        assert False
    except ValueError as e:
        pass


def test_update() -> None:
    class TestHyperparams(Hyperparams):
        field1: str = HP(
            description="First field",
            default="value",
        )
        field2: int = HP(
            description="Violating field",
            default=5,
        )
        field3: float = HP(
            description="Other violating field",
            default=0.9,
        )

    p1 = TestHyperparams()

    # In place: False, Validate: False
    p2 = p1.update({"field2": 7, "field3": 2.3}, inplace=False, validate=False)
    assert p1 is not p2
    assert p1.field1 == "value"
    assert p1.field2 == 5
    assert p1.field3 == approx(0.9)
    assert p2.field1 == "value"
    assert p2.field2 == 7
    assert p2.field3 == approx(2.3)

    p2 = p1.update({"field2": "hi", "field3": "x"}, inplace=False, validate=False)
    assert p1 is not p2
    assert p1.field1 == "value"
    assert p1.field2 == 5
    assert p1.field3 == approx(0.9)
    assert p2.field1 == "value"
    assert p2.field2 == "hi"
    assert p2.field3 == "x"

    # In place: False, Validate: True
    p2 = p1.update({"field2": 7, "field3": 2.3}, inplace=False, validate=True)
    assert p1 is not p2
    assert p1.field1 == "value"
    assert p1.field2 == 5
    assert p1.field3 == approx(0.9)
    assert p2.field1 == "value"
    assert p2.field2 == 7
    assert p2.field3 == approx(2.3)
    try:
        p2 = p1.update({"field2": "hi", "field3": "x"}, inplace=False, validate=True)
        assert False
    except ValidationError as err:
        assert len(err.errors()) == 1
        assert err.errors()[0]["loc"][0] == "field2"
    try:
        p2 = p1.update({"field3": "x"}, inplace=False, validate=True)
        assert False
    except ValidationError as err:
        assert len(err.errors()) == 1
        assert err.errors()[0]["loc"][0] == "field3"

    # In place: True, Validate: False
    p1 = TestHyperparams()
    p2 = p1.update({"field2": 7, "field3": 2.3}, inplace=True, validate=False)
    assert p1 is p2
    assert p1.field1 == "value"
    assert p1.field2 == 7
    assert p1.field3 == approx(2.3)
    assert p2.field1 == "value"
    assert p2.field2 == 7
    assert p2.field3 == approx(2.3)

    p1 = TestHyperparams()
    p2 = p1.update({"field2": "hi", "field3": "x"}, inplace=True, validate=False)
    assert p1 is p2
    assert p1.field1 == "value"
    assert p1.field2 == "hi"
    assert p1.field3 == "x"
    assert p2.field1 == "value"
    assert p2.field2 == "hi"
    assert p2.field3 == "x"

    # In place: True, Validate: True
    p1 = TestHyperparams()
    p2 = p1.update({"field2": 7, "field3": 2.3}, inplace=True, validate=True)
    assert p1 is p2
    assert p1.field1 == "value"
    assert p1.field2 == 7
    assert p1.field3 == approx(2.3)
    assert p2.field1 == "value"
    assert p2.field2 == 7
    assert p2.field3 == approx(2.3)

    p1 = TestHyperparams()
    try:
        p2 = p1.update({"field2": "hi", "field3": "x"}, inplace=True, validate=True)
        assert False
    except ValidationError as err:
        assert len(err.errors()) == 1
        assert err.errors()[0]["loc"][0] == "field2"
    assert p1.field1 == "value"
    assert p1.field2 == 5
    assert p1.field3 == approx(0.9)
    try:
        p2 = p1.update({"field3": "x"}, inplace=True, validate=True)
        assert False
    except ValidationError as err:
        assert len(err.errors()) == 1
        assert err.errors()[0]["loc"][0] == "field3"
    assert p1.field1 == "value"
    assert p1.field2 == 5
    assert p1.field3 == approx(0.9)


def test_tunable_params() -> None:
    class TestHyperparams(Hyperparams):
        field1: int = HP(
            description="Not tunable",
            default=2,
        )
        field2: float = HP(
            description="Tunable float",
            default=0.3,
            search_space=[0, 1],
        )
        field3: str = HP(
            description="Tunable choices",
            default="medium",
            tunable=True,
            choices=["small", "medium", "large"],
        )
        field4: str = HP(
            description="Not tunable choices",
            default="large",
            choices=["small", "medium", "large"],
        )
        field5: bool = HP(
            description="Tunable bool",
            default=False,
            tunable=True,
        )
        field6: bool = HP(
            description="Not tunable bool",
            default=True,
        )

    p = TestHyperparams()
    tunable_params = {k: v for k, v in p._tunable_params()}
    assert tunable_params == {
        "field2": HyperparamInfo(
            tunable=True,
            search_space=[0, 1],
            default=0.3,
        ),
        "field3": HyperparamInfo(
            tunable=True,
            default="medium",
            choices=["small", "medium", "large"],
        ),
        "field5": HyperparamInfo(
            tunable=True,
            default=False,
            choices=[False, True],
        ),
    }
