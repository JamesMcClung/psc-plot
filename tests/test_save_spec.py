import pytest
from conftest import CONFIG_2D

from lib.data.compile import compile_action_nodes
from lib.parsing.parse import parse_args

_BASE = ["pfd", "hx_fc", "-i", "t=-1", "-v", "y", "time=", "-q"]


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
