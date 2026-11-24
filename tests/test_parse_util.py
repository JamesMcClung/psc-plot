import argparse

import pytest

from lib.parsing import parse_util


@pytest.mark.parametrize(
    "val, expected",
    [
        ("dir", True),
        ("name", True),
        ("a1", True),
        ("_x", True),
        ("a.b", True),
        ("", False),
        ("a.", False),
        (".a", False),
        ("out/fig", False),
        ("a-b", False),
        ("(a)", False),
        ("1a", True),
    ],
)
def test_is_identifier(val, expected):
    assert parse_util.is_identifier(val) is expected


@pytest.mark.parametrize(
    "arg, expected",
    [
        ("pfd::ey_ec", ("pfd", "ey_ec")),
        ("run5/pfd::", ("run5/pfd", "")),
        ("::ey_ec", ("", "ey_ec")),
        ("ey_ec", (None, "ey_ec")),
    ],
)
def test_parse_scoped(arg, expected):
    assert parse_util.parse_scoped(arg, "fmt") == expected


def test_parse_scoped_rejects_two_scopes():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_util.parse_scoped("a::b::c", "fmt")
