import argparse
import typing

import xarray as xr

from ...bp_util import BP_DIMS
from ..plugin_base import PluginBp
from ..registry import plugin


@plugin(
    "--roll",
    metavar="dim_name=window_size",
    help="plot the rolling average against this dimension with this window size",
)
class Roll(PluginBp):
    def __init__(self, dim_name: str, roll_window: int):
        self.dim_name = dim_name
        self.window_size = roll_window

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling({self.dim_name: self.window_size}).mean()

    @classmethod
    def parse(cls, arg: str) -> typing.Self:
        split_str = arg.split("=")

        if len(split_str) != 2:
            raise argparse.ArgumentTypeError(f"Expected value of form 'dim_name=window_size'; got '{arg}'")

        [dim_name, window_size] = split_str

        if dim_name not in BP_DIMS:
            raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{dim_name}'")

        try:
            window_size = int(window_size)
        except:
            raise argparse.ArgumentTypeError(f"Expected window_size to be an integer; got '{window_size}'")

        return cls(dim_name, window_size)
