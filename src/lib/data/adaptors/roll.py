import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.dimension import DIMENSIONS
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Roll(BareAdaptor):
    def __init__(self, dim_names_to_window_size: dict[str, int]):
        self.dim_names_to_window_size = dim_names_to_window_size

    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling(self.dim_names_to_window_size).mean()

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={bin_size}" for dim_name, bin_size in self.dim_names_to_window_size.items())
        return [f"roll_{subfrags}"]


ROLL_FORMAT = "dim_name=window_size"


@arg_parser(
    dest="adaptors",
    flags="--roll",
    metavar=ROLL_FORMAT,
    help="plot the rolling average against the given dimension with the given window size",
    nargs="+",
)
def parse(args: list[str]) -> Roll:
    dim_names_to_window_size = {}
    for arg in args:
        [dim_name, window_size_arg] = parse_util.parse_assignment(arg, ROLL_FORMAT)

        parse_util.check_value(dim_name, "dim_name", DIMENSIONS)
        window_size = parse_util.parse_number(window_size_arg, "window_size", int)

        dim_names_to_window_size[dim_name] = window_size

    return Roll(dim_names_to_window_size)
