import argparse
import typing

import xarray as xr

from ...bp_util import BP_DIMS
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class PosSlice(PluginBp):
    def __init__(self, dim_name: str, lower_inclusive: float | None, upper_exclusive: float | None):
        self.dim_name = dim_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.sel({self.dim_name: slice(self.lower_inclusive, self.upper_exclusive)})


@plugin_parser(
    "--pos-slice",
    metavar="dim_name=lower:upper",
    help="restrict data along given the dimension to a slice, specified by lower (inclusive) and upper (exclusive) positions (both optional)",
)
def parse_pos_slice(arg: str) -> PosSlice:
    split_arg = arg.split("=")

    if len(split_arg) != 2:
        _fail_format(arg)

    [dim_name, slice_arg] = split_arg

    if dim_name not in BP_DIMS:
        raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{dim_name}'")

    split_slice_arg = slice_arg.split(":")
    if len(split_slice_arg) != 2:
        _fail_format(arg)

    [lower_arg, upper_arg] = split_slice_arg
    lower = _parse_bound(lower_arg, "lower")
    upper = _parse_bound(upper_arg, "upper")

    if upper is not None and lower is not None and upper <= lower:
        raise argparse.ArgumentTypeError(f"Expected lower < upper; got lower={lower}, upper={upper}")

    return PosSlice(dim_name, lower, upper)


def _fail_format(arg: str):
    raise argparse.ArgumentTypeError(f"Expected value of form 'dim_name=lower:upper'; got '{arg}'")


def _parse_bound(bound_arg: str, which_bound: typing.Literal["upper", "lower"]) -> float | None:
    if bound_arg == "":
        return None

    try:
        return float(bound_arg)
    except:
        raise argparse.ArgumentTypeError(f"Expected {which_bound} to be a float or absent; got '{bound_arg}'")
