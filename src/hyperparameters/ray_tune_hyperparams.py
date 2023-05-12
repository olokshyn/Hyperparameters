from typing import Any

from ray import tune

from hyperparameters.hyperparams import HyperparamsProtocol


class RayTuneHyperparamsMixin(HyperparamsProtocol):
    @classmethod
    def ray_tune_param_space(cls) -> dict[str, Any]:
        param_space = {}
        for name, info in cls._tunable_params():
            if info.search_space is not None:
                param_space[name] = info.search_space
            elif info.choices is not None:
                param_space[name] = tune.choice(info.choices)
            elif info.default is not None:
                param_space[name] = info.default
        return param_space

    @classmethod
    def ray_tune_best_values(cls) -> dict[str, Any]:
        return {
            name: info.default
            for name, info in cls._tunable_params()
            if info.default is not None
        }
