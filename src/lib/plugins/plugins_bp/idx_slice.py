import argparse
import typing

import xarray as xr

from ...bp_util import BP_DIMS
from ..plugin_base import PluginBp
from ..registry import plugin


@plugin(
    "--idx-slice",
    metavar="dim_name=lower:upper",
    help="restrict data along given the dimension to a slice, specified by lower (inclusive) and upper (exclusive) indices (both optional)",
)
class IdxSlice(PluginBp):
    def __init__(self, dim_name: str, lower_inclusive: int | None, upper_exclusive: int | None):
        self.dim_name = dim_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.isel({self.dim_name: slice(self.lower_inclusive, self.upper_exclusive)})

    @classmethod
    def parse(cls, arg: str) -> typing.Self:
        split_arg = arg.split("=")

        if len(split_arg) != 2:
            cls._fail_format(arg)

        [dim_name, slice_arg] = split_arg

        if dim_name not in BP_DIMS:
            raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{dim_name}'")

        split_slice_arg = slice_arg.split(":")
        if len(split_slice_arg) != 2:
            cls._fail_format(arg)

        [lower_arg, upper_arg] = split_slice_arg
        lower = cls._parse_bound(lower_arg, "lower")
        upper = cls._parse_bound(upper_arg, "upper")

        if upper is not None and lower is not None and upper <= lower:
            raise argparse.ArgumentTypeError(f"Expected lower < upper; got lower={lower}, upper={upper}")

        return cls(dim_name, lower, upper)

    @classmethod
    def _fail_format(cls, arg: str):
        raise argparse.ArgumentTypeError(f"Expected value of form 'dim_name=lower:upper'; got '{arg}'")

    @classmethod
    def _parse_bound(cls, bound_arg: str, which_bound: typing.Literal["upper", "lower"]) -> int | None:
        if bound_arg == "":
            return None

        try:
            return int(bound_arg)
        except:
            raise argparse.ArgumentTypeError(f"Expected {which_bound} to be an integer or absent; got '{bound_arg}'")
