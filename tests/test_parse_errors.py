import argparse

import pytest

from lib.parsing.args_registry import get_store_combined_args_action
from lib.parsing.parse import parse_args


def test_bad_versus_arg_exits_cleanly():
    """A validation failure inside a multi-arg adaptor must render as an argparse
    error, not escape as an uncaught ArgumentTypeError traceback."""
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["pfd", "hx_fc", "-v", "loc=oops"])

    assert excinfo.value.code == 2


def test_bad_versus_arg_message_names_the_flag(capsys):
    with pytest.raises(SystemExit):
        parse_args(["pfd", "hx_fc", "-v", "loc=oops"])

    err = capsys.readouterr().err
    error_line = err.rsplit("error: ", 1)[-1]
    assert "-v" in error_line
    assert "--versus" in error_line
    assert "i,j" in err


def _combining_parser():
    parser = argparse.ArgumentParser(prog="t")
    parser.add_argument("-s", nargs="*", default=None, dest="save", action=get_store_combined_args_action(tuple))
    return parser


def test_store_combined_args_action_distinguishes_absent_bare_and_valued():
    parser = _combining_parser()
    assert parser.parse_args([]).save is None
    assert parser.parse_args(["-s"]).save == ()
    assert parser.parse_args(["-s", "a", "b"]).save == ("a", "b")


def test_store_combined_args_action_stores_rather_than_appends():
    """Unlike get_combine_args_action, a second occurrence replaces rather than appends."""
    assert _combining_parser().parse_args(["-s", "a", "-s", "b"]).save == ("b",)


def test_store_combined_args_action_routes_argument_type_error(capsys):
    def combiner(values):
        raise argparse.ArgumentTypeError("bad value")

    parser = argparse.ArgumentParser(prog="t")
    parser.add_argument("-s", "--save", nargs="*", default=None, dest="save", action=get_store_combined_args_action(combiner))

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["-s", "x"])

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    error_line = err.rsplit("error: ", 1)[-1]
    assert "-s" in error_line
    assert "--save" in error_line
    assert "bad value" in error_line
