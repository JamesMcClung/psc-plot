import pytest
from conftest import CONFIG_2D

from lib.data.compile import compile_action_nodes
from lib.data.node import RenderPlotNode, SavePlotNode, ShowPlotNode
from lib.parsing.parse import parse_args

_ANIMATED = ["pfd", "hx_fc", "-v", "y"]
_STATIC = ["pfd", "hx_fc", "-i", "t=-1", "-v", "y", "time="]


def test_profile_flag_defaults_off():
    assert parse_args(_ANIMATED).profile is False
    assert parse_args([*_ANIMATED, "--profile"]).profile is True


def test_profile_renders_offscreen_instead_of_showing():
    [node] = compile_action_nodes(parse_args([*_ANIMATED, "--profile"]), CONFIG_2D)
    assert isinstance(node, RenderPlotNode)


def test_profile_with_save_only_saves(tmp_path):
    [node] = compile_action_nodes(parse_args([*_ANIMATED, "--profile", "-s", f"{tmp_path}/"]), CONFIG_2D)
    assert isinstance(node, SavePlotNode)


def test_without_profile_still_shows():
    assert any(isinstance(node, ShowPlotNode) for node in compile_action_nodes(parse_args(_ANIMATED), CONFIG_2D))


def test_profile_and_dask_graph_conflict(capsys):
    with pytest.raises(SystemExit) as exit_info:
        compile_action_nodes(parse_args([*_ANIMATED, "--profile", "--dask-graph"]), CONFIG_2D)
    assert exit_info.value.code == 1
    assert "error: --profile and --dask-graph are mutually exclusive" in capsys.readouterr().err


@pytest.mark.parametrize("args_list", [_ANIMATED, _STATIC])
def test_render_offscreen_runs(args_list):
    [node] = compile_action_nodes(parse_args([*args_list, "--profile"]), CONFIG_2D)
    node.pull()
