# Hyperparameters

Are you tired of repeating hyperparameters in code, `argparse` definitions, and hyperparameter tunning libraries?

`Hyperparameters` lets you define your hyperparameters once and use everywhere! Moreover, you get type linting and spelling checks for free!

## Quickstart

Install `Hyperparameters`:
```bash
pip install hyperparameters
```

You need to install the `ray.tune` package separately if you want to use the `ray.tune` hypertunning integration:
```bash
pip install -U "ray[tune]"
```

Define your parameters once using the `Hyperparams` class:

```python
from argparse import ArgumentParser
from typing import Optional

from hyperparameters import HP, Hyperparams


class MyHyperparams(Hyperparams):
    epochs: int = HP(
        "Number of epochs to train for",
        default=5,
    )
    lr: float = HP(
        "Learning rate",
        default=1e-3,
    )
    tokenizer: str = HP(
        "HF tokenizer to use",
        default="BPE",
        choices=["BPE", "WordPiece"],
    )
    train_data_path: str = HP(
        "Path to the training dataset",
    )
    use_dropout: bool = HP(
        "Whether the dropout layers should be activated",
        default=True,
    )
    pretrained_weights: Optional[str] = HP(
        "Path to the pretrained model weights, if any",
        default=None,
    )


parser = ArgumentParser()
MyHyperparams.add_arguments(parser)
params = MyHyperparams.from_arguments(parser.parse_args())

# access parameters as typed attributes
params.train_data_path

# convert to a dictionary
print(params.dict())
```

Let's see the registered arguments by running the code above with `--help`:
```
usage: example.py [-h] [--epochs EPOCHS] [--lr LR] [--tokenizer {BPE,WordPiece}] --train-data-path TRAIN_DATA_PATH [--use-dropout | --no-use-dropout]
                  [--pretrained-weights PRETRAINED_WEIGHTS]

options:
  -h, --help            show this help message and exit
  --epochs EPOCHS       Number of epochs to train for
  --lr LR               Learning rate
  --tokenizer {BPE,WordPiece}
                        HF tokenizer to use
  --train-data-path TRAIN_DATA_PATH
                        Path to the training dataset
  --use-dropout         Whether the dropout layers should be activated
  --no-use-dropout      Disable: Whether the dropout layers should be activated
  --pretrained-weights PRETRAINED_WEIGHTS
                        Path to the pretrained model weights, if any
```
As can be seen from the above, `Hyperparameters` takes care of low level details for you:

1. The `--train-data-path` parameter is required because we didn't provide a default value for it. All other parameters are optional.
2. Even though the default value for `--pretrained-weights` is `None`, this parameter is optional. However, we had to use the `Optional[str]` type hint.
3. You can provide the `--use-dropout` or the `--no-use-dropout` flag, but not both at the same time. Neither flag is required, as the `use_dropout` parameter has a default value.
4. The `--tokenizer` parameter can only be `BPE` or `WordPiece`. Providing any other value results in an error.
5. The data types of the parameters are parsed from strings and validated according to the type hints in the `MyHyperparams` class. 
6. The default values are used whenever an argument is ommitted. Let's check that by running with `--train-data-path mydata/`: the script prints: `{'epochs': 5, 'lr': 0.001, 'tokenizer': 'BPE', 'train_data_path': 'mydata/', 'use_dropout': True, 'pretrained_weights': None}`.


### Default values and required parameters

1. If a default value is omitted completely, the parameter will be required.
2. Otherwise, if any default value is specified, even `None`, the parameter will be optional.
3. You must use the `Optional` type hint if the default value is `None`.
4. You can't have `bool` parameters with `None` as default. Flags that can be `None` just don't make any sense.
5. You can't have choice parameters with `None` as default. If you need this, just add a "null" value to the list of choices.


## Hypertunning
Different hypertunning libraries provide different APIs for defining search spaces. `Hyperparameters` can be easily extended to support any hypertunning library. You can do it yourself following the steps discussed below - it's easy! The `ray.tune` library is supported out of the box.

When defining hypertunable parameters with `Hyperparameters`, make sure to inherit from both the `Hyperparams` class and the mixin class specific to your hypertunning library. Here is an example for `ray.tune`:
```python
from hyperparameters import HP, Hyperparams
from hyperparameters.ray_tune_hyperparams import RayTuneHyperparamsMixin


class MyHyperparams(Hyperparams, RayTuneHyperparamsMixin):
    ...
```

Next, you can specify the search spaces:

1. use the hypertunning library API to describe the search space and provide this object to the `HP(..., search_space=)` parameter;
2. if you already specify the `HP(..., choices=[])` parameter you can treat the possible choices as a search space by setting the `HP(..., tunable=True)` parameter.
3. for `bool` fields just set the `HP(..., tunable=True)` parameter, which is equivallent to `HP(..., tunable=True, choices=[False, True])`.

Note that when using the `search_space` parameter, you don't need to use the `tunable` parameter.

Finally, you are ready to use the mixin-specific methods to extract information about your search spaces. For `ray.tune` these are:

1. `.ray_tune_param_space()` method that returns a dictionary describing the search space.
2. `.ray_tune_best_values()` method that returns a dictionary of the best values to start hypertunning from.

Here is a complete example of defining parameters hypertunable with `ray.tune`:
```python
from ray import tune

from hyperparameters import HP, Hyperparams
from hyperparameters.ray_tune_hyperparams import RayTuneHyperparamsMixin


class MyHyperparams(Hyperparams, RayTuneHyperparamsMixin):
    lr: float = HP(
        "Learning rate",
        default=1e-3,
        search_space=tune.loguniform(1e-5, 1e-2),
    )
    layers_num: int = HP(
        "Number of model layers",
        default=8,
        tunable=True,
        choices=[4, 8, 16, 24],
    )
    use_dropout: bool = HP(
        "Whether the dropout layers should be activated",
        default=True,
        tunable=True,
    )


params = MyHyperparams()

# Search space config that ray.tune understands
params.ray_tune_param_space()

# Best values to start the hypertunning from
params.ray_tune_best_values()
```

### Supporting other hypertunning libraries

In `Hyperparameters`, the logic specific to hypertunning libraries is implemented with mixin classes. This means that you can add many mixins to your parameters and support several hypertunning libraries at once.

The best place to start is to review the implementation of the `RayTuneHyperparamsMixin` class in `hyperparameters/ray_tune_hyperparams.py`.

The class implementing a new hypertunning library must:

1. Inherit from `hyperparameters.hyperparams.HyperparamsProtocol`.
2. Provide class methods for converting the params data stored in `hyperparameters.hyperparams.HyperparamInfo` structure into a format that the hypertunning library understands.
3. Use the `cls._tunable_params()` to get the info about the parameters.
4. Wrap `info.choices` in a proper type for the hypertunning library.
5. Provide a method for returning the best parameter values to start the hypertunning from.
