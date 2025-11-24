import xarray as xr

from ....dimension import DIMENSIONS
from ...adaptor import AtomicAdaptor
from .. import parse_util
from ..registry import adaptor_parser


class IdxSlice(AtomicAdaptor):
    def __init__(self, dim_name: str, lower_inclusive: int | None, upper_exclusive: int | None):
        self.dim_name = dim_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply_atomic(self, da: xr.DataArray) -> xr.DataArray:
        return da.isel({self.dim_name: slice(self.lower_inclusive, self.upper_exclusive)})

    def get_name_fragments(self) -> list[str]:
        lower = f"{self.lower_inclusive}" if self.lower_inclusive is not None else ""
        upper = f"{self.upper_exclusive}" if self.upper_exclusive is not None else ""
        return [f"slice_{self.dim_name}={lower}:{upper}"]


IDX_SLICE_FORMAT = "dim_name=lower:upper"


@adaptor_parser(
    "--idx-slice",
    metavar=IDX_SLICE_FORMAT,
    help="restrict data along the given dimension to a slice, specified by lower (inclusive) and upper (exclusive) indices (both optional)",
)
def parse_idx_slice(arg: str) -> IdxSlice:
    split_arg = arg.split("=")

    if len(split_arg) != 2:
        parse_util.fail_format(arg, IDX_SLICE_FORMAT)

    [dim_name, slice_arg] = split_arg

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    split_slice_arg = slice_arg.split(":")
    if len(split_slice_arg) != 2:
        parse_util.fail_format(arg, IDX_SLICE_FORMAT)

    [lower_arg, upper_arg] = split_slice_arg
    lower = parse_util.parse_optional_number(lower_arg, "lower", int)
    upper = parse_util.parse_optional_number(upper_arg, "upper", int)

    parse_util.check_order(lower, upper, "lower", "upper")

    return IdxSlice(dim_name, lower, upper)
