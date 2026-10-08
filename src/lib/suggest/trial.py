import multiprocessing
import sys
from collections.abc import Callable
from dataclasses import dataclass

import matplotlib

from lib.config import ConfigValue, PscPlotConfig
from lib.parsing.parse import parse_args
from lib.plotting.animated_plot import AnimatedPlot
from lib.profiling.profiler import Profiler, StageRecord
from lib.profiling.sampler import ProcessTreeSampler
from lib.run.actions import RenderPlot
from lib.run.compile import compile_plot_pipeline
from lib.run.dask_setup import configure_dask

# frames per trial: enough to rank schedulers by per-frame cost without paying for the whole animation
TRIAL_FRAMES = 6


@dataclass(frozen=True)
class TrialRun:
    total: StageRecord
    n_frames: int  # the plot's full frame count, not the number rendered


@dataclass(frozen=True)
class TrialFailure:
    reason: str


type TrialResult = TrialRun | TrialFailure


def run_trial(argv: list[str], config_mapping: dict[str, ConfigValue]) -> TrialRun:
    """Run the pipeline and its first TRIAL_FRAMES frames offscreen under the config, and return the profiled total."""
    config = PscPlotConfig.from_mapping(config_mapping)
    configure_dask(config)
    plot_pipeline = compile_plot_pipeline(parse_args(argv), config)
    with ProcessTreeSampler() as sampler:
        profiler = Profiler(sampler)
        with profiler.run():
            plot = plot_pipeline.run_plot()
            n_frames = plot.n_frames if isinstance(plot, AnimatedPlot) else 1
            RenderPlot(max_frames=TRIAL_FRAMES).run(plot)
    return TrialRun(profiler.total, n_frames)


def _child(connection, target: Callable[..., TrialResult], args: tuple) -> None:
    # stdout is reserved for the suggested config
    sys.stdout = sys.stderr
    matplotlib.use("Agg")
    try:
        result = target(*args)
    except Exception as e:
        result = TrialFailure(f"{type(e).__name__}: {e}")
    connection.send(result)
    connection.close()


def _spawn(target: Callable[..., TrialResult], *args) -> TrialResult:
    """Run target(*args) in a fresh process, so each trial gets its own dask setup and its own peak RSS."""
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(sender, target, args))
    process.start()
    sender.close()
    try:
        result = receiver.recv()
    except EOFError:  # the process died without sending, e.g. OOM-killed
        result = None
    process.join()
    if result is None:
        return TrialFailure(f"exited with code {process.exitcode}")
    return result


def spawn_trial(argv: list[str], config: PscPlotConfig) -> TrialResult:
    return _spawn(run_trial, argv, config.to_mapping())
