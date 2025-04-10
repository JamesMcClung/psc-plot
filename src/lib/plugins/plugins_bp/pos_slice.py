import argparse

import xarray as xr

from ...bp_util import BP_DIMS
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class PosSlice(PluginBp):
    def __init__(self, dim_name: str, lower_inclusive: float | None, upper_exclusive: float | None):
        self.dim_name = dim_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.sel({self.dim_name: slice(self.lower_inclusive, self.upper_exclusive)})


_POS_SLICE_FORMAT = "dim_name=lower:upper"


@plugin_parser(
    "--pos-slice",
    metavar=_POS_SLICE_FORMAT,
    help="restrict data along given the dimension to a slice, specified by lower (inclusive) and upper (exclusive) positions (both optional)",
)
def parse_pos_slice(arg: str) -> PosSlice:
    split_arg = arg.split("=")

    if len(split_arg) != 2:
        parse_util.fail_format(arg, _POS_SLICE_FORMAT)

    [dim_name, slice_arg] = split_arg

    if dim_name not in BP_DIMS:
        raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{dim_name}'")

    split_slice_arg = slice_arg.split(":")
    if len(split_slice_arg) != 2:
        parse_util.fail_format(arg, _POS_SLICE_FORMAT)

    [lower_arg, upper_arg] = split_slice_arg
    lower = parse_util.parse_optional_number(lower_arg, "lower", float)
    upper = parse_util.parse_optional_number(upper_arg, "upper", float)

    if upper is not None and lower is not None and upper <= lower:
        raise argparse.ArgumentTypeError(f"Expected lower < upper; got lower={lower}, upper={upper}")

    return PosSlice(dim_name, lower, upper)
