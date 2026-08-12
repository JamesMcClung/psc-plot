import pytest

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
    assert "-v/--versus" in err
    assert "i,j" in err
