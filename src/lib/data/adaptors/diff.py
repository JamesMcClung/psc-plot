from dataclasses import dataclass
from typing import Literal

import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser

type Boundary = Literal["truncate", "periodic", "pad"]
BOUNDARY_KEYS: tuple[Boundary, ...] = Boundary.__value__.__args__


@dataclass
class _Diff1d:
    dim_key: str
    dir: Literal[-1, 1]
    boundary: Boundary

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        shifted = da.roll({self.dim_key: -self.dir}, roll_coords=False)
        diff = self.dir * (shifted - da)

        if self.boundary == "truncate":
            isel = slice(1, None) if self.dir == -1 else slice(0, -1)
            return diff.isel({self.dim_key: isel})

        if self.boundary == "pad":
            boundary_idx = 0 if self.dir == -1 else -1
            diff[{self.dim_key: boundary_idx}] = 0.0

        return diff


class Diff(BareAdaptor):
    def __init__(self, diffs_1d: list[_Diff1d]):
        self.diffs_1d = diffs_1d

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        dims = ",".join(diff_1d.dim_key for diff_1d in self.diffs_1d)
        return Latex(f"\\Delta_{{{dims}}}{metadata.active_var_info.display}")

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for diff_1d in self.diffs_1d:
            da = diff_1d.apply_field_bare(da)
        return da

    def get_name_fragments(self) -> list[str]:
        parts = []
        prev_boundary: Boundary | None = None
        for diff_1d in self.diffs_1d:
            if diff_1d.boundary != prev_boundary:
                parts.append(diff_1d.boundary)
                prev_boundary = diff_1d.boundary
            sign = "+" if diff_1d.dir > 0 else "-"
            parts.append(f"{diff_1d.dim_key}={sign}{abs(diff_1d.dir)}")
        return [f"diff_{'_'.join(parts)}"]


DIR_TO_SHIFT = {"+": 1, "-": -1}
DIFF_FORMAT = f"[{' | '.join(BOUNDARY_KEYS)}] dim_key[,dim_key...]={set(DIR_TO_SHIFT)} [...]"


@arg_parser(
    dest="adaptors",
    flags="--diff",
    metavar=DIFF_FORMAT,
    help=f"Take the forward ('+') or backward ('-') difference along the given dimension(s). {'/'.join(BOUNDARY_KEYS)} markers determine how to handle boundaries for subsequent specs (default: {BOUNDARY_KEYS[0]}).",
    nargs="+",
)
def parse(args: list[str]) -> Diff:
    diffs_1d: list[_Diff1d] = []
    boundary = BOUNDARY_KEYS[0]

    for arg in args:
        if arg in BOUNDARY_KEYS:
            boundary = arg
            continue

        dims_arg, dir_arg = parse_util.parse_assignment(arg, DIFF_FORMAT)

        parse_util.parse_value(dir_arg, "dir", DIR_TO_SHIFT.keys())
        dir = DIR_TO_SHIFT[dir_arg]

        for dim in parse_util.parse_comma_separated_list(dims_arg):
            parse_util.parse_identifier(dim, "dim_key")
            diffs_1d.append(_Diff1d(dim, dir, boundary))

    return Diff(diffs_1d)
