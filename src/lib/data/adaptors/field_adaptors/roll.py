import xarray as xr

from ....dimension import DIMENSIONS
from .. import parse_util
from ..adaptor import Adaptor
from ..registry import adaptor_parser


class Roll(Adaptor):
    def __init__(self, dim_name: str, roll_window: int):
        self.dim_name = dim_name
        self.window_size = roll_window

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling({self.dim_name: self.window_size}).mean()

    def get_name_fragments(self) -> list[str]:
        return ["roll_{self.dim_name}={self.window_size}"]


ROLL_FORMAT = "dim_name=window_size"


@adaptor_parser(
    "--roll",
    metavar=ROLL_FORMAT,
    help="plot the rolling average against the given dimension with the given window size",
)
def parse(arg: str) -> Roll:
    split_str = arg.split("=")

    if len(split_str) != 2:
        parse_util.fail_format(arg, ROLL_FORMAT)

    [dim_name, window_size_arg] = split_str

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    window_size = parse_util.parse_number(window_size_arg, "window_size", int)

    return Roll(dim_name, window_size)
