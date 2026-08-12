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
