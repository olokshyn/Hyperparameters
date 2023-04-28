from typing import Any

from ray import tune

from hyperparams.hyperparams import Hyperparams


class RayTuneHyperparamsMixin:
    @classmethod
    def ray_tune_param_space(cls: type[Hyperparams]) -> dict[str, Any]:  # type: ignore
        param_space = {}
        for name, info in cls._tunable_params():
            if info.search_space is not None:
                param_space[name] = info.search_space
            elif info.choices is not None:
                param_space[name] = tune.choice(info.choices)
            elif info.default is not None:
                param_space[name] = info.default
        return param_space
