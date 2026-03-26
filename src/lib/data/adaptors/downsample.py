import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.dimension import DIMENSIONS
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Downsample(BareAdaptor):
    def __init__(self, dim_name: str, bin_size: int):
        self.dim_name = dim_name
        self.bin_size = bin_size

    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.coarsen({self.dim_name: self.bin_size}, boundary="pad").mean()

    def get_name_fragments(self) -> list[str]:
        return [f"downsample_{self.dim_name}={self.bin_size}"]


BIN_SIZE = "bin_size"
DOWNSAMPLE_FORMAT = f"dim_name={BIN_SIZE}"


@arg_parser(
    dest="adaptors",
    flags="--downsample",
    metavar=DOWNSAMPLE_FORMAT,
    help=f"downsample by a factor of {BIN_SIZE}",
)
def parse(arg: str) -> Downsample:
    [dim_name, bin_size_arg] = parse_util.parse_assignment(arg, DOWNSAMPLE_FORMAT)

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    bin_size = parse_util.parse_number(bin_size_arg, BIN_SIZE, int)

    return Downsample(dim_name, bin_size)
