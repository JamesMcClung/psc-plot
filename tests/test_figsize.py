import argparse

import pytest

from lib.parsing.parse import parse_args
from lib.parsing.parse_figsize import parse_figsize
from lib.plotting.layout.options import DEFAULT_DPI, FigSizeSpec


@pytest.mark.parametrize(
    "arg, expected",
    [
        ("auto", FigSizeSpec(None, None)),
        ("auto,auto", FigSizeSpec(None, None)),
        ("8,auto", FigSizeSpec(8.0, None)),
        ("auto,3in", FigSizeSpec(None, 3.0)),
        ("6.5in,4", FigSizeSpec(6.5, 4.0)),
    ],
)
def test_parse_figsize(arg: str, expected: FigSizeSpec):
    assert parse_figsize(arg) == expected


@pytest.mark.parametrize("arg", ["8", "0,3", "-1,3", "8cm,3", ",3", "a,b", "1,2,3"])
def test_parse_figsize_rejects(arg: str):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_figsize(arg)


def test_defaults():
    args = parse_args(["pfd", "hx_fc"])
    assert args.figsize == FigSizeSpec(None, None)
    assert args.dpi == DEFAULT_DPI == 100.0


def test_flags_parse():
    args = parse_args(["pfd", "hx_fc", "--figsize", "4,auto", "--dpi", "50"])
    assert args.figsize == FigSizeSpec(4.0, None)
    assert args.dpi == 50.0


def test_save_dpi_is_gone():
    with pytest.raises(SystemExit):
        parse_args(["pfd", "hx_fc", "--save-dpi", "50"])
