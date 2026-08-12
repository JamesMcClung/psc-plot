import argparse
from pathlib import Path

import pytest

from lib.parsing.parse_save import SaveSpec, parse_save


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
