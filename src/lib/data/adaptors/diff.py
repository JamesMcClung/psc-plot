from typing import Literal

import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser

type Boundary = Literal["periodic", "pad"]
BOUNDARY_KEYS: tuple[Boundary, ...] = Boundary.__value__.__args__
type DimKey = str
type Dir = Literal[-1, 1]
type DiffSpec = tuple[DimKey, Dir, Boundary]


def _diff_one(da: xr.DataArray, dim: DimKey, dir: Dir, boundary: Boundary) -> xr.DataArray:
    shifted = da.roll({dim: -dir}, roll_coords=False)

    if boundary == "pad":
        boundary_idx = 0 if dir == -1 else -1
        shifted = shifted.copy()
        shifted[{dim: boundary_idx}] = da[{dim: boundary_idx}]

    return dir * (shifted - da)


class Diff(BareAdaptor):
    def __init__(self, specs: list[DiffSpec]):
        self.specs = specs

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        dims = ",".join(spec[0] for spec in self.specs)
        return Latex(f"\\Delta_{{{dims}}}{metadata.active_var_info.display}")

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for dim, dir, boundary in self.specs:
            da = _diff_one(da, dim, dir, boundary)
        return da

    def get_name_fragments(self) -> list[str]:
        parts = []
        prev_boundary: Boundary | None = None
        for dim, dir, boundary in self.specs:
            if boundary != prev_boundary:
                parts.append(boundary)
                prev_boundary = boundary
            sign = "+" if dir > 0 else "-"
            parts.append(f"{dim}={sign}{abs(dir)}")
        return [f"diff_{'_'.join(parts)}"]


DIR_TO_SHIFT = {"+": 1, "-": -1}
DIFF_FORMAT = f"[{' | '.join(BOUNDARY_KEYS)}] dim_name[,dim_name...]={set(DIR_TO_SHIFT)} [...]"


@arg_parser(
    dest="adaptors",
    flags="--diff",
    metavar=DIFF_FORMAT,
    help=f"Take the forward ('+') or backward ('-') difference along the given dimension(s). {'/'.join(BOUNDARY_KEYS)} markers determine how to handle boundaries for subsequent specs (default: {BOUNDARY_KEYS[0]}).",
    nargs="+",
)
def parse(args: list[str]) -> Diff:
    specs: list[DiffSpec] = []
    boundary = BOUNDARY_KEYS[0]

    for arg in args:
        if args in BOUNDARY_KEYS:
            boundary = arg
            continue

        dims_arg, dir_arg = parse_util.parse_assignment(arg, DIFF_FORMAT)

        parse_util.check_value(dir_arg, "dir", DIR_TO_SHIFT.keys())
        dir = DIR_TO_SHIFT[dir_arg]

        for dim in parse_util.parse_comma_separated_list(dims_arg):
            parse_util.check_identifier(dim, "dim_name")
            specs.append((dim, dir, boundary))

    return Diff(specs)
