import pytest

from lib.profiling.profiler import TOTAL, Profiler, StageRecord, profile_stage
from lib.profiling.sampler import SampleWindow


class FakeSampler:
    """A sampler whose CPU and RSS the test sets by hand."""

    def __init__(self):
        self.cpu = 0.0
        self.rss = 100
        self.windows: list[SampleWindow] = []

    def set_rss(self, rss: int):
        self.rss = rss
        for window in self.windows:
            window.peak_rss = max(window.peak_rss, rss)

    def open_window(self) -> SampleWindow:
        window = SampleWindow(cpu_start=self.cpu, peak_rss=self.rss)
        self.windows.append(window)
        return window

    def close_window(self, window: SampleWindow) -> tuple[float, int]:
        self.windows.remove(window)
        return self.cpu - window.cpu_start, window.peak_rss


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def setup():
    sampler, clock = FakeSampler(), FakeClock()
    return sampler, clock, Profiler(sampler, clock=clock)


def test_stage_records_wall_cpu_peak(setup):
    sampler, clock, profiler = setup
    with profiler.run():
        with profile_stage("a"):
            clock.now += 2.0
            sampler.cpu += 3.0
            sampler.set_rss(500)
            sampler.set_rss(200)
    assert profiler.records == [StageRecord("a", 2.0, 3.0, 500)]


def test_nested_stage_is_swallowed(setup):
    sampler, clock, profiler = setup
    with profiler.run():
        with profile_stage("outer"):
            clock.now += 1.0
            with profile_stage("inner"):
                clock.now += 1.0
    assert profiler.records == [StageRecord("outer", 2.0, 0.0, 100)]


def test_exclusive_stage_subtracts_nested_stages(setup):
    sampler, clock, profiler = setup
    with profiler.run():
        with profile_stage("finish", exclusive=True):
            clock.now += 1.0
            with profile_stage("frame"):
                clock.now += 2.0
                sampler.cpu += 2.0
                with profile_stage("deeper"):
                    clock.now += 1.0
            sampler.cpu += 0.5
    assert profiler.records == [StageRecord("frame", 3.0, 2.0, 100), StageRecord("finish", 1.0, 0.5, 100)]


def test_profile_stage_without_profiler_is_noop():
    with profile_stage("a"):
        pass


def test_run_records_total(setup):
    sampler, clock, profiler = setup
    with profiler.run():
        with profile_stage("a"):
            clock.now += 1.0
        clock.now += 1.0
        sampler.cpu += 4.0
    assert profiler.total == StageRecord(TOTAL, 2.0, 4.0, 100)


def test_run_resets_active_profiler_on_error(setup):
    _, clock, profiler = setup
    with pytest.raises(RuntimeError):
        with profiler.run():
            raise RuntimeError
    with profile_stage("after"):
        clock.now += 1.0
    assert profiler.records == []
