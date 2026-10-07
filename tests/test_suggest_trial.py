import os

from conftest import CONFIG_2D

from lib.suggest.trial import TrialFailure, TrialRun, _spawn, run_trial, spawn_trial

_ANIMATED = ["pfd", "hx_fc", "-v", "y"]


def _die():
    os._exit(3)


def test_run_trial_reports_the_total_and_full_frame_count():
    result = run_trial(_ANIMATED, CONFIG_2D.to_mapping())
    assert result.n_frames == 11
    assert result.total.wall > 0


def test_spawn_trial():
    result = spawn_trial(_ANIMATED, CONFIG_2D)
    assert isinstance(result, TrialRun)
    assert result.n_frames == 11


def test_spawn_trial_reports_an_exception():
    result = spawn_trial(["pfd", "no_such_var", "-v", "y"], CONFIG_2D)
    assert isinstance(result, TrialFailure)
    assert "no_such_var" in result.reason


def test_spawn_reports_a_process_that_dies():
    assert _spawn(_die) == TrialFailure("exited with code 3")
