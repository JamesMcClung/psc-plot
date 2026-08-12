"""Everything about saving a figure, from the innermost layer outward:

1. `parse_save` — the pure `--save` argument grammar, no data and no pipeline.
2. `get_save_file_stem` — the filename derived from the node graph's `name_fragments`.
3. The whole pipeline — `compile_action_nodes` through to a file on disk.
"""

import argparse
from pathlib import Path

import pytest
from conftest import CONFIG_2D, make_save

from lib.data.compile import compile_action_nodes, compile_plot_node
from lib.parsing.parse import parse_args
from lib.parsing.parse_save import SaveSpec, parse_save

# --- 1. The --save argument grammar -------------------------------------------------


@pytest.mark.parametrize(
    "args, expected",
    [
        # bare -s: every component defaulted
        ([], SaveSpec()),
        ([""], SaveSpec()),
        # fragment: each component alone
        (["out/"], SaveSpec(dir=Path("out"))),
        (["fig"], SaveSpec(name="fig")),
        ([".gif"], SaveSpec(format="gif")),
        # fragment: combinations
        (["out/fig.gif"], SaveSpec(dir=Path("out"), name="fig", format="gif")),
        (["out/.gif"], SaveSpec(dir=Path("out"), format="gif")),
        (["/out/fig.png"], SaveSpec(dir=Path("/out"), name="fig", format="png")),
        (["../out/"], SaveSpec(dir=Path("../out"))),
        # rule 2 fallthrough: all-dot segments are dirs, not stems
        (["."], SaveSpec(dir=Path("."))),
        ([".."], SaveSpec(dir=Path(".."))),
        (["./.."], SaveSpec(dir=Path("./.."))),
        # last dot wins; trailing dot is absorbed into the stem
        (["fig.tar.gz"], SaveSpec(name="fig.tar", format="gz")),
        (["fig."], SaveSpec(name="fig.")),
        # keys
        (["dir=out", "name=fig", "format=gif"], SaveSpec(dir=Path("out"), name="fig", format="gif")),
        (["out/", "name=fig.i"], SaveSpec(dir=Path("out"), name="fig.i")),
        (["name=abc=efg"], SaveSpec(name="abc=efg")),
        # key detection: a non-identifier before "=" means it is a fragment
        (["out/fig=x"], SaveSpec(dir=Path("out"), name="fig=x")),
        (["a-b=c"], SaveSpec(name="a-b=c")),
        # a leading "~" expands; bash does not do it after "=" or inside quotes
        (["dir=~/figs"], SaveSpec(dir=Path.home() / "figs")),
        (["dir=~"], SaveSpec(dir=Path.home())),
        (["~/figs/"], SaveSpec(dir=Path.home() / "figs")),
        # "~" naming no real user stays literal rather than raising
        (["dir=~nosuchuser42/x"], SaveSpec(dir=Path("~nosuchuser42/x"))),
    ],
)
def test_parse_save(args, expected):
    assert parse_save(args) == expected


@pytest.mark.parametrize(
    "args, message_fragment",
    [
        # identifier before "=" that is not a known key
        (["stem=foo"], "save key"),
        (["ext=gif"], "save key"),
        (["a.b=c"], "save key"),
        # component set twice
        (["out/", "dir=other"], "at most once"),
        (["out/fig.gif", "format=png"], "at most once"),
        (["name=a", "fig"], "at most once"),
        # more than one fragment
        (["fig", "other"], "at most one path fragment"),
        # per-key validation
        (["name=a/b"], "name"),
        (["name=.."], "name"),
        (["name="], "name"),
        (["format=a.b"], "format"),
        (["format=a/b"], "format"),
        (["format="], "format"),
        (["dir="], "dir"),
    ],
)
def test_parse_save_errors(args, message_fragment):
    with pytest.raises(argparse.ArgumentTypeError, match=message_fragment):
        parse_save(args)


# --- 2. The derived filename stem ---------------------------------------------------


@pytest.mark.parametrize(
    "args_list, expected_stem",
    [
        (["pfd", "hx_fc"], "pfd__hx_fc-v_y,z"),
        (["pfd", "hx_fc", "--nan0"], "pfd__hx_fc-nan0-v_y,z"),
        (["pfd", "hx_fc", "--scale", "log"], "pfd__hx_fc-scale_log-v_y,z"),
        (["pfd", "hx_fc", "-v", "y", "z", "time="], "pfd__hx_fc-v_y,z;time="),
    ],
)
def test_save_file_stem(args_list, expected_stem):
    actual_stem = compile_plot_node(parse_args(args_list), CONFIG_2D).get_save_file_stem()
    assert actual_stem == expected_stem


# --- 3. End to end, through the pipeline to a file ----------------------------------

_BASE = ["pfd", "hx_fc", "-i", "t=-1", "-v", "y", "time=", "-q"]


def test_save_static_png(tmp_path):
    """Saving a static plot produces a .png file."""
    path = make_save("pfd hx_fc -i t=-1 -v y time=".split(), tmp_path, "png")
    assert path.exists()
    assert path.suffix == ".png"


def test_save_animated_gif(tmp_path):
    """Saving an animated plot as gif produces a file with the correct number of frames."""
    from PIL import Image

    path = make_save("pfd hx_fc -v y".split(), tmp_path, "gif")
    assert path.exists()
    assert path.suffix == ".gif"

    with Image.open(path) as img:
        assert img.n_frames == 11


def test_no_save_flag_produces_no_action_nodes():
    assert compile_action_nodes(parse_args(_BASE), CONFIG_2D) == []


def test_save_uses_derived_stem_by_default(tmp_path):
    [node] = compile_action_nodes(parse_args([*_BASE, "-s", f"{tmp_path}/"]), CONFIG_2D)
    node.pull()
    assert (tmp_path / f"{node.get_save_file_stem()}.png").exists()


def test_save_name_and_format_override_the_output_path(tmp_path):
    [node] = compile_action_nodes(parse_args([*_BASE, "-s", f"{tmp_path}/", "name=myfig", "format=png"]), CONFIG_2D)
    node.pull()
    assert (tmp_path / "myfig.png").exists()


def test_save_fragment_sets_dir_name_and_ext(tmp_path):
    [node] = compile_action_nodes(parse_args([*_BASE, "-s", f"{tmp_path}/myfig.png"]), CONFIG_2D)
    node.pull()
    assert (tmp_path / "myfig.png").exists()


def test_save_name_is_not_sanitized(tmp_path):
    """A ':' in a derived stem is rewritten by sanitize_stem; an explicit name is not."""
    [node] = compile_action_nodes(parse_args([*_BASE, "-s", f"{tmp_path}/", "name=a:b"]), CONFIG_2D)
    node.pull()
    assert (tmp_path / "a:b.png").exists()


def test_save_format_flag_is_gone():
    with pytest.raises(SystemExit):
        parse_args([*_BASE, "--save-format", "gif"])


def test_save_incompatible_format_falls_back_to_default(tmp_path):
    """A static plot only allows 'png'; requesting 'jpg' should warn and fall back."""
    [node] = compile_action_nodes(parse_args([*_BASE, "-s", f"{tmp_path}/", "name=myfig", "format=jpg"]), CONFIG_2D)
    with pytest.warns(UserWarning, match="jpg is incompatible with the data; reverting to default"):
        node.pull()
    assert (tmp_path / "myfig.png").exists()
