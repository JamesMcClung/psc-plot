import multiprocessing
import sys
from collections.abc import Callable
from dataclasses import dataclass

import matplotlib

from lib.config import ConfigValue, PscPlotConfig
from lib.parsing.parse import parse_args
from lib.plotting.animated_plot import AnimatedPlot
from lib.profiling.profiler import FRAME_RENDER, Profiler, StageRecord
from lib.profiling.sampler import ProcessTreeSampler
from lib.run.actions import RenderPlot
from lib.run.compile import compile_plot_pipeline
from lib.run.dask_setup import configure_dask

# frames per trial: the first, which pays one-off costs, then enough to project the per-frame cost without paying for the whole animation
TRIAL_FRAMES = 6


@dataclass(frozen=True)
class TrialRun:
    total: StageRecord
    n_frames: int  # the plot's full frame count, not the number rendered
    frames_rendered: int
    later_frames_wall: float  # the wall of every rendered frame but the first

    @property
    def projected_wall(self) -> float:
        """The wall time to render all n_frames: the measured total, plus each unrendered frame at the mean wall of the later rendered frames."""
        if self.frames_rendered < 2:
            return self.total.wall
        per_frame = self.later_frames_wall / (self.frames_rendered - 1)
        return self.total.wall + per_frame * (self.n_frames - self.frames_rendered)


@dataclass(frozen=True)
class TrialFailure:
    reason: str


type TrialResult = TrialRun | TrialFailure


def _split_frames(records: list[StageRecord]) -> tuple[int, float]:
    """The number of frames rendered, and the wall of every frame but the first. A frame ends with its render, so everything up to the first render, including the pipeline, plot init and the first frame, counts as startup."""
    renders = [i for i, record in enumerate(records) if record.name == FRAME_RENDER]
    return len(renders), sum(record.wall for record in records[renders[0] + 1 :])


def run_trial(argv: list[str], config_mapping: dict[str, ConfigValue]) -> TrialRun:
    """Run the pipeline and its first TRIAL_FRAMES frames offscreen under the config, and return the profiled total and frames."""
    config = PscPlotConfig.from_mapping(config_mapping)
    configure_dask(config)
    plot_pipeline = compile_plot_pipeline(parse_args(argv), config)
    with ProcessTreeSampler() as sampler:
        profiler = Profiler(sampler)
        with profiler.run():
            plot = plot_pipeline.run_plot()
            n_frames = plot.n_frames if isinstance(plot, AnimatedPlot) else 1
            RenderPlot(max_frames=TRIAL_FRAMES).run(plot)
    return TrialRun(profiler.total, n_frames, *_split_frames(profiler.records))


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
