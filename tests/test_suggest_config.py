import sys

import pytest
import yaml
from conftest import _DATA_DIR

from lib import cli
from lib.config import CONFIG_KEYS, CONFIG_PATH_KEY

_ANIMATED = ["pfd", "hx_fc", "-v", "y"]
_STATIC = ["pfd", "hx_fc", "-i", "t=-1", "-v", "y", "time="]


def _run_cli(monkeypatch, argv: list[str], scheduler: str = "synchronous") -> None:
    for key in (*CONFIG_KEYS, CONFIG_PATH_KEY, "PBS_JOBID", "SLURM_JOB_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PSC_PLOT_DATA_DIR", str(_DATA_DIR / "test-2d"))
    monkeypatch.setenv("PSC_PLOT_FFMPEG_BIN", "")
    monkeypatch.setenv("PSC_PLOT_DASK_SCHEDULER", scheduler)
    # an SGE job with 2 slots, so trials stay small and the workers line is $NSLOTS
    monkeypatch.setenv("JOB_ID", "1")
    monkeypatch.setenv("SGE_ROOT", "/sge")
    monkeypatch.setenv("NSLOTS", "2")
    monkeypatch.setattr(sys, "argv", ["psc-plot", *argv])
    cli.main()


def test_without_pipeline_prints_only_yaml(monkeypatch, capsys):
    _run_cli(monkeypatch, ["--suggest-config"])
    out = capsys.readouterr().out
    values = yaml.safe_load(out)
    assert set(values) == set(CONFIG_KEYS)
    assert values["PSC_PLOT_DATA_DIR"] == "."
    assert values["PSC_PLOT_DASK_NUM_WORKERS"] == "$NSLOTS"
    assert "environment-based guess" in out


def test_without_pipeline_never_sets_up_dask(monkeypatch, capsys):
    # the current config says distributed, which isn't importable; only a dask setup in the parent would fail
    monkeypatch.setitem(sys.modules, "dask.distributed", None)
    _run_cli(monkeypatch, ["--suggest-config"], scheduler="distributed")
    assert yaml.safe_load(capsys.readouterr().out)["PSC_PLOT_DASK_SCHEDULER"] == "threads"


def test_with_pipeline_times_every_candidate(monkeypatch, capsys):
    from lib.suggest.candidates import candidate_schedulers

    _run_cli(monkeypatch, [*_ANIMATED, "--suggest-config"])
    captured = capsys.readouterr()
    values = yaml.safe_load(captured.out)
    assert values["PSC_PLOT_DASK_SCHEDULER"] in candidate_schedulers()
    assert "(6 of 11 frames, after a warm-up run)" in captured.out
    assert "measured: pfd hx_fc -v y " in captured.out
    for scheduler in candidate_schedulers():
        assert f"trial {scheduler}" in captured.err


def test_static_pipeline(monkeypatch, capsys):
    _run_cli(monkeypatch, [*_STATIC, "--suggest-config"])
    assert "(1 of 1 frames, after a warm-up run)" in capsys.readouterr().out


def test_failing_pipeline_stops_after_the_warm_up(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit_info:
        _run_cli(monkeypatch, ["pfd", "no_such_var", "-v", "y", "--suggest-config"])
    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "error: the pipeline failed under the current config:" in captured.err
    assert "trial " not in captured.err
    assert captured.out == ""


def test_save_is_rejected(monkeypatch, capsys, tmp_path):
    with pytest.raises(SystemExit):
        _run_cli(monkeypatch, [*_ANIMATED, "--suggest-config", "-s", f"{tmp_path}/"])
    assert "error: --suggest-config never saves" in capsys.readouterr().err


def test_conflicts_with_profile(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit_info:
        _run_cli(monkeypatch, [*_ANIMATED, "--suggest-config", "--profile"])
    assert exit_info.value.code == 2
