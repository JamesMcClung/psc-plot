import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from lib.profiling.sampler import ProcessTreeSampler

PLOT_INIT = "plot init"
FRAME_UPDATE = "frame.update"
FRAME_RENDER = "frame.render"
FINISH = "finish"
TOTAL = "total"


@dataclass(frozen=True)
class StageRecord:
    name: str
    wall: float
    cpu: float
    peak_rss: int


# The profiler of the run in progress, if any. Instrumented code calls profile_stage() instead of taking a profiler.
_ACTIVE: ContextVar["Profiler | None"] = ContextVar("_ACTIVE_PROFILER", default=None)


class Profiler:
    def __init__(self, sampler: ProcessTreeSampler, clock: Callable[[], float] = time.perf_counter):
        self.sampler = sampler
        self.clock = clock
        self.records: list[StageRecord] = []
        self.total: StageRecord | None = None
        self._depth = 0

    @contextmanager
    def run(self) -> Iterator["Profiler"]:
        """Make this the active profiler, and record the whole run as `total`."""
        token = _ACTIVE.set(self)
        window = self.sampler.open_window()
        start = self.clock()
        try:
            yield self
        finally:
            wall = self.clock() - start
            cpu, peak_rss = self.sampler.close_window(window)
            self.total = StageRecord(TOTAL, wall, cpu, peak_rss)
            _ACTIVE.reset(token)

    @contextmanager
    def stage(self, name: str, *, exclusive: bool = False) -> Iterator[None]:
        """Record a stage. A stage inside another records nothing, so its cost stays in the outer one, except directly inside an `exclusive` stage, which records its nested stages and subtracts them from its own wall and CPU."""
        if self._depth > 0:
            yield
            return

        window = self.sampler.open_window()
        start = self.clock()
        first_nested = len(self.records)
        if not exclusive:
            self._depth += 1
        try:
            yield
        finally:
            if not exclusive:
                self._depth -= 1
            wall = self.clock() - start
            cpu, peak_rss = self.sampler.close_window(window)
            nested = self.records[first_nested:]
            wall -= sum(record.wall for record in nested)
            cpu -= sum(record.cpu for record in nested)
            self.records.append(StageRecord(name, wall, cpu, peak_rss))


@contextmanager
def profile_stage(name: str, *, exclusive: bool = False) -> Iterator[None]:
    """Record a stage on the active profiler; do nothing when none is running."""
    profiler = _ACTIVE.get()
    if profiler is None:
        yield
        return
    with profiler.stage(name, exclusive=exclusive):
        yield
