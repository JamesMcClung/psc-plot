from typing import Literal

import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser

type Boundary = Literal["periodic", "pad"]


def _recenter_one(da: xr.DataArray, dim: str, interp_dir: int, boundary: Boundary) -> xr.DataArray:
    shifted = da.roll({dim: -interp_dir}, roll_coords=False)

    if boundary == "pad":
        boundary_idx = 0 if interp_dir == -1 else -1
        shifted = shifted.copy()
        shifted[{dim: boundary_idx}] = da[{dim: boundary_idx}]

    return 0.5 * (da + shifted)


class Recenter(BareAdaptor):
    def __init__(self, specs: list[tuple[str, int, Boundary]]):
        self.specs = specs

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for dim, interp_dir, boundary in self.specs:
            da = _recenter_one(da, dim, interp_dir, boundary)
        return da

    def get_name_fragments(self) -> list[str]:
        parts = []
        prev_boundary: Boundary | None = None
        for dim, interp_dir, boundary in self.specs:
            if boundary != prev_boundary:
                parts.append(boundary)
                prev_boundary = boundary
            sign = "+" if interp_dir > 0 else "-"
            parts.append(f"{dim}={sign}{abs(interp_dir)}")
        return [f"recenter_{'_'.join(parts)}"]


PERIODIC_MARKER = "periodic"
PAD_MARKER = "pad"
DIR_TO_SHIFT = {"+": 1, "-": -1}
RECENTER_FORMAT = f"[{PERIODIC_MARKER} | {PAD_MARKER}] dim_name[,dim_name...]={set(DIR_TO_SHIFT)} [...]"


@arg_parser(
    dest="adaptors",
    flags="--recenter",
    metavar=RECENTER_FORMAT,
    help=f"Average each value with its neighbor in the given direction per dimension(s). '{PAD_MARKER}'/'{PERIODIC_MARKER}' markers determine how to handle boundaries for subsequent specs (default: {PERIODIC_MARKER}).",
    nargs="+",
)
def parse(args: list[str]) -> Recenter:
    specs: list[tuple[str, int, Boundary]] = []
    boundary: Boundary = "periodic"

    for arg in args:
        if arg == PERIODIC_MARKER:
            boundary = "periodic"
            continue
        if arg == PAD_MARKER:
            boundary = "pad"
            continue

        dims_arg, interp_dir_arg = parse_util.parse_assignment(arg, RECENTER_FORMAT)

        parse_util.parse_value(interp_dir_arg, "dir", DIR_TO_SHIFT.keys())
        interp_dir = DIR_TO_SHIFT[interp_dir_arg]

        for dim in parse_util.parse_comma_separated_list(dims_arg):
            parse_util.parse_identifier(dim, "dim_name")
            specs.append((dim, interp_dir, boundary))

    return Recenter(specs)
