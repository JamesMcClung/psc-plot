import pytest

from lib.data.adaptors.copy import Copy
from lib.data.adaptors.fourier import Fourier
from lib.data.adaptors.math_op import MathOp
from lib.data.adaptors.recenter import Recenter
from lib.parsing.parse import StepParseError, parse_steps


def test_steps_parse_in_order():
    [copy, pow_] = parse_steps(["--copy a=hx_fc", "--pow 2"])
    assert isinstance(copy, Copy) and (copy.new_key, copy.old_key) == ("a", "hx_fc")
    assert isinstance(pow_, MathOp) and pow_.rhs == 2.0


def test_multi_value_step_is_one_adaptor():
    [fourier] = parse_steps(["--fourier x y z"])
    assert isinstance(fourier, Fourier) and fourier.dim_keys == ["x", "y", "z"]


def test_steps_do_not_leak_into_each_other():
    # --recenter uses the combine-args action, which appends to the namespace's list
    [first, second] = parse_steps(["--recenter y=-", "--recenter z=+"])
    assert isinstance(first, Recenter) and first.specs == [("y", -1, "periodic")]
    assert isinstance(second, Recenter) and second.specs == [("z", 1, "periodic")]


def test_empty_steps():
    assert parse_steps([]) == []


@pytest.mark.parametrize(
    "step, match",
    [
        ("-v y", "versus"),
        ("--fit 10:20", "unrecognized"),
        ("-s", "unrecognized"),
        ("-q", "unrecognized"),
        ("--dask-graph", "unrecognized"),
        ("hx_fc", "unrecognized"),
        ("--idx y=abc", "--idx y=abc"),
    ],
)
def test_rejected_steps(step, match):
    with pytest.raises(StepParseError, match=match):
        parse_steps([step])
