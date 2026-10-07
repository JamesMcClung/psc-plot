import datetime
import shlex
import sys
from dataclasses import replace
from functools import partial

from lib.config import PscPlotConfig
from lib.profiling.environment import EnvironmentReport
from lib.profiling.worker_count import WorkerCount
from lib.run.usage_error import UsageError
from lib.suggest.candidates import candidate_schedulers, guess_scheduler
from lib.suggest.suggestion import ConfigSuggestion, Measurement, fastest
from lib.suggest.trial import TRIAL_FRAMES, TrialFailure, spawn_trial


def _progress(message: str) -> None:
    print(f"suggest-config: {message}", file=sys.stderr, flush=True)


def suggest_config(argv: list[str], has_pipeline: bool, config: PscPlotConfig, environment: EnvironmentReport) -> ConfigSuggestion:
    """Suggest a config: with a pipeline (`argv`, without --suggest-config), by timing it under each candidate scheduler; else from the environment alone."""
    workers = WorkerCount.from_environment(environment)
    suggestion = partial(ConfigSuggestion, host=environment.host, date=datetime.date.today(), workers=workers, config=config)
    if not has_pipeline:
        return suggestion(scheduler=guess_scheduler(workers.value), measurement=None)

    # pays for cold file caches before anything is timed, and catches pipeline errors before every trial repeats them
    _progress("warm-up run under the current config")
    warm_up = spawn_trial(argv, config)
    if isinstance(warm_up, TrialFailure):
        raise UsageError(f"the pipeline failed under the current config: {warm_up.reason}")

    trials = {}
    for scheduler in candidate_schedulers():
        _progress(f"trial {scheduler} with {workers.value} workers")
        trials[scheduler] = spawn_trial(argv, replace(config, dask_scheduler=scheduler, dask_num_workers=workers.value))

    scheduler = fastest(trials)
    if scheduler is None:
        raise UsageError("every trial failed: " + "; ".join(f"{name}: {result.reason}" for name, result in trials.items()))

    measurement = Measurement(shlex.join(argv), min(TRIAL_FRAMES, warm_up.n_frames), warm_up.n_frames, trials)
    return suggestion(scheduler=scheduler, measurement=measurement)
