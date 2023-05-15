from typing import Any

from ray import tune

from hyperparameters.hyperparams import HyperparamsProtocol


class RayTuneHyperparamsMixin(HyperparamsProtocol):
    def ray_tune_param_space(self, use_current_values: bool = True) -> dict[str, Any]:
        param_space = {}
        for name, info in self._tunable_params():
            if info.search_space is not None:
                param_space[name] = info.search_space
            elif info.choices is not None:
                param_space[name] = tune.choice(info.choices)
            else:
                if use_current_values:
                    param_space[name] = getattr(self, name)
                else:
                    param_space[name] = info.default
        return param_space

    def ray_tune_best_values(self, use_current_values: bool = True) -> dict[str, Any]:
        if use_current_values:
            return {name: getattr(self, name) for name, _ in self._tunable_params()}
        else:
            return {
                name: info.default
                for name, info in self._tunable_params()
                if info.default is not None
            }
