import sys

import pytest
from conftest import _DATA_DIR, CONFIG_2D

from lib import cli
from lib.config import CONFIG_KEYS, CONFIG_PATH_KEY
from lib.parsing.parse import parse_args
from lib.profiling.profiler import FINISH, FRAME_RENDER, FRAME_UPDATE, PLOT_INIT, Profiler
from lib.profiling.sampler import ProcessTreeSampler
from lib.run.actions import RenderPlot, SavePlot, ShowPlot
from lib.run.compile import compile_run

_ANIMATED = ["pfd", "hx_fc", "-v", "y"]
_STATIC = ["pfd", "hx_fc", "-i", "t=-1", "-v", "y", "time="]


def test_profile_renders_offscreen_instead_of_showing():
    [action] = compile_run(parse_args([*_ANIMATED, "--profile"]), CONFIG_2D).plot_actions
    assert isinstance(action, RenderPlot)


def test_profile_with_save_only_saves(tmp_path):
    [action] = compile_run(parse_args([*_ANIMATED, "--profile", "-s", f"{tmp_path}/"]), CONFIG_2D).plot_actions
    assert isinstance(action, SavePlot)


def test_without_profile_still_shows():
    assert any(isinstance(action, ShowPlot) for action in compile_run(parse_args(_ANIMATED), CONFIG_2D).plot_actions)


def test_profile_and_dask_graph_conflict(capsys):
    with pytest.raises(SystemExit) as exit_info:
        compile_run(parse_args([*_ANIMATED, "--profile", "--dask-graph"]), CONFIG_2D)
    assert exit_info.value.code == 1
    assert "error: --profile and --dask-graph are mutually exclusive" in capsys.readouterr().err


def _profile(args_list: list[str]) -> Profiler:
    run = compile_run(parse_args([*args_list, "--profile"]), CONFIG_2D)
    with ProcessTreeSampler() as sampler:
        profiler = Profiler(sampler)
        with profiler.run():
            run.execute()
    return profiler


def _count(profiler: Profiler, name: str) -> int:
    return sum(record.name == name for record in profiler.records)


def test_animated_offscreen_profile():
    profiler = _profile(_ANIMATED)
    names = [record.name for record in profiler.records]
    adaptor_names = names[: names.index(PLOT_INIT)]
    assert adaptor_names[0].startswith("With")
    assert adaptor_names[-1].startswith("Versus")
    assert _count(profiler, FRAME_RENDER) == 11
    assert _count(profiler, FRAME_UPDATE) == 12  # Animation.save redraws frame 0 as its initial draw
    assert _count(profiler, FINISH) == 0
    assert profiler.total.wall >= sum(record.wall for record in profiler.records) * 0.99


def test_animated_save_profile(tmp_path):
    profiler = _profile([*_ANIMATED, "-s", f"{tmp_path}/out.gif"])
    assert (tmp_path / "out.gif").exists()
    assert _count(profiler, FRAME_RENDER) == 11
    assert _count(profiler, FINISH) == 1


def test_static_save_profile(tmp_path):
    profiler = _profile([*_STATIC, "-s", f"{tmp_path}/out.png"])
    assert (tmp_path / "out.png").exists()
    assert _count(profiler, FRAME_RENDER) == 1
    assert _count(profiler, FRAME_UPDATE) == 0
    assert _count(profiler, FINISH) == 1


def test_static_offscreen_profile():
    profiler = _profile(_STATIC)
    assert _count(profiler, FRAME_RENDER) == 1


def _run_cli(monkeypatch, argv: list[str]):
    for key in (*CONFIG_KEYS, CONFIG_PATH_KEY):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PSC_PLOT_DATA_DIR", str(_DATA_DIR / "test-2d"))
    monkeypatch.setenv("PSC_PLOT_FFMPEG_BIN", "")
    monkeypatch.setenv("PSC_PLOT_DASK_SCHEDULER", "synchronous")
    monkeypatch.setattr(sys, "argv", ["psc-plot", *argv])
    cli.main()


def test_cli_profile_without_pipeline_reports_environment_only(monkeypatch, capsys):
    _run_cli(monkeypatch, ["--profile"])
    out = capsys.readouterr().out
    assert "== environment ==" in out
    assert "== pipeline ==" not in out
    assert "PSC_PLOT_DATA_DIR" in out  # an env override


def test_cli_profile_with_pipeline(monkeypatch, capsys):
    _run_cli(monkeypatch, [*_ANIMATED, "--profile"])
    out = capsys.readouterr().out
    assert "== environment ==" in out
    assert "frame render ×11" in out
    assert "frame update ×12" in out
    assert out.rstrip().splitlines()[-1].startswith("total")


@pytest.mark.parametrize("save", [False, True])
def test_every_canvas_draw_is_in_a_stage(monkeypatch, tmp_path, save):
    """matplotlib redraws after each frame (_post_draw -> draw_idle, synchronous on Agg); that draw must land in a stage, not between stages or in finish."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    from lib.profiling.profiler import _ACTIVE

    draw = FigureCanvasAgg.draw
    unattributed = []

    def recording_draw(self, *args, **kwargs):
        if _ACTIVE.get()._depth == 0:
            unattributed.append(self)
        return draw(self, *args, **kwargs)

    monkeypatch.setattr(FigureCanvasAgg, "draw", recording_draw)
    _profile([*_ANIMATED, *(["-s", f"{tmp_path}/out.gif"] if save else [])])
    assert unattributed == []
