import xarray as xr

from ...bp_util import BP_DIMS
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Roll(PluginBp):
    def __init__(self, dim_name: str, roll_window: int):
        self.dim_name = dim_name
        self.window_size = roll_window

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling({self.dim_name: self.window_size}).mean()


ROLL_FORMAT = "dim_name=window_size"


@plugin_parser(
    "--roll",
    metavar=ROLL_FORMAT,
    help="plot the rolling average against this dimension with this window size",
)
def parse(arg: str) -> Roll:
    split_str = arg.split("=")

    if len(split_str) != 2:
        parse_util.fail_format(arg, ROLL_FORMAT)

    [dim_name, window_size_arg] = split_str

    parse_util.check_value(dim_name, "dim_name", BP_DIMS)

    window_size = parse_util.parse_number(window_size_arg, "window_size", int)

    return Roll(dim_name, window_size)
