import xarray as xr

from ....dimension import DIMENSIONS
from ...adaptor import AtomicAdaptor
from .. import parse_util
from ..registry import adaptor_parser


class Roll(AtomicAdaptor):
    def __init__(self, dim_name: str, roll_window: int):
        self.dim_name = dim_name
        self.window_size = roll_window

    def apply_atomic(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling({self.dim_name: self.window_size}).mean()

    def get_name_fragments(self) -> list[str]:
        return [f"roll_{self.dim_name}={self.window_size}"]


ROLL_FORMAT = "dim_name=window_size"


@adaptor_parser(
    "--roll",
    metavar=ROLL_FORMAT,
    help="plot the rolling average against the given dimension with the given window size",
)
def parse(arg: str) -> Roll:
    [dim_name, window_size_arg] = parse_util.parse_assignment(arg, ROLL_FORMAT)

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    window_size = parse_util.parse_number(window_size_arg, "window_size", int)

    return Roll(dim_name, window_size)
