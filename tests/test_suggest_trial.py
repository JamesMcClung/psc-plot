import os

from conftest import CONFIG_2D

from lib.profiling.profiler import FRAME_REDRAW, FRAME_RENDER, FRAME_UPDATE, PLOT_INIT, StageRecord
from lib.suggest.trial import TRIAL_FRAMES, TrialFailure, TrialRun, _spawn, _split_frames, run_trial, spawn_trial

_ANIMATED = ["pfd", "hx_fc", "-v", "y"]


def _die():
    os._exit(3)


def _record(name: str, wall: float) -> StageRecord:
    return StageRecord(name, wall, 0.0, 0)


def test_run_trial_reports_the_total_and_frames():
    result = run_trial(_ANIMATED, CONFIG_2D.to_mapping())
    assert result.n_frames == 11
    assert result.frames_rendered == TRIAL_FRAMES
    assert 0 < result.later_frames_wall < result.total.wall < result.projected_wall


def test_split_frames_counts_everything_through_the_first_render_as_startup():
    # matplotlib's init draw updates frame 0 before the first frame's own update
    records = [_record(PLOT_INIT, 5.0), _record(FRAME_UPDATE, 1.0)]
    for _ in range(3):
        records += [_record(FRAME_UPDATE, 2.0), _record(FRAME_REDRAW, 0.5), _record(FRAME_RENDER, 0.25)]
    assert _split_frames(records) == (3, 5.5)


def test_projected_wall_extrapolates_the_later_frames():
    # 10s startup and 1s/frame beats 1s startup and 2s/frame over 100 frames, though not over the 6 rendered
    slow_start = TrialRun(_record("total", 10.0 + 6 * 1.0), 100, 6, 5 * 1.0)
    fast_start = TrialRun(_record("total", 1.0 + 6 * 2.0), 100, 6, 5 * 2.0)
    assert slow_start.total.wall > fast_start.total.wall
    assert slow_start.projected_wall == 110.0
    assert fast_start.projected_wall == 201.0


def test_projected_wall_of_a_static_plot_is_its_total():
    assert TrialRun(_record("total", 3.0), 1, 1, 0.0).projected_wall == 3.0


def test_spawn_trial_reports_an_exception():
    result = spawn_trial(["pfd", "no_such_var", "-v", "y"], CONFIG_2D)
    assert isinstance(result, TrialFailure)
    assert "no_such_var" in result.reason


def test_spawn_reports_a_process_that_dies():
    assert _spawn(_die) == TrialFailure("exited with code 3")
