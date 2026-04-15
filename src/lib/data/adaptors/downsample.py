import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.dimension import DIM_DEFAULTS
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Downsample(BareAdaptor):
    def __init__(self, dim_names_to_bin_size: dict[str, int]):
        self.dim_names_to_bin_size = dim_names_to_bin_size

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.coarsen(self.dim_names_to_bin_size, boundary="pad").mean()

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={bin_size}" for dim_name, bin_size in self.dim_names_to_bin_size.items())
        return [f"downsample_{subfrags}"]


BIN_SIZE = "bin_size"
DOWNSAMPLE_FORMAT = f"dim_name={BIN_SIZE}"


@arg_parser(
    dest="adaptors",
    flags="--downsample",
    metavar=DOWNSAMPLE_FORMAT,
    help=f"downsample by a factor of {BIN_SIZE}",
    nargs="+",
)
def parse(args: list[str]) -> Downsample:
    dim_names_to_bin_size = {}
    for arg in args:
        [dim_name, bin_size_arg] = parse_util.parse_assignment(arg, DOWNSAMPLE_FORMAT)

        parse_util.check_value(dim_name, "dim_name", DIM_DEFAULTS)
        bin_size = parse_util.parse_number(bin_size_arg, BIN_SIZE, int)

        dim_names_to_bin_size[dim_name] = bin_size

    return Downsample(dim_names_to_bin_size)
