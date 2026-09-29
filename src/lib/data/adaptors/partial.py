import numpy as np
import xarray as xr

from lib.data.adaptors.diff import BOUNDARY_KEYS, DIFF_FORMAT, DiffBase, _Diff1d, parse_diffs_1d
from lib.parsing.args_registry import arg_parser


def _spacing(diff_1d: _Diff1d, coord: xr.DataArray) -> xr.DataArray:
    """The coordinate difference matching `diff_1d`, per cell, so nonuniform grids work. Covers every cell; division aligns it to whichever cells the boundary kept."""
    c = coord.values
    if len(c) < 2:
        raise ValueError(f"--partial needs at least 2 points along '{diff_1d.dim_key}'; got {len(c)}")
    spacing = diff_1d.dir * (np.roll(c, -diff_1d.dir) - c)
    # the wrap-around cell spans the domain boundary, where the true spacing is unknown; interpolate from the cells on either side of it
    boundary_idx = 0 if diff_1d.dir == -1 else -1
    spacing[boundary_idx] = ((c[1] - c[0]) + (c[-1] - c[-2])) / 2
    return xr.DataArray(spacing, coords={diff_1d.dim_key: c}, dims=diff_1d.dim_key)


class Partial(DiffBase):
    symbol = "\\partial"
    fragment_prefix = "partial"

    def apply_1d(self, diff_1d: _Diff1d, da: xr.DataArray) -> xr.DataArray:
        return diff_1d.apply_field_bare(da) / _spacing(diff_1d, da.coords[diff_1d.dim_key])


@arg_parser(
    dest="adaptors",
    flags="--partial",
    metavar=DIFF_FORMAT,
    help=f"Like --diff, but divide each difference by the corresponding grid spacing along its dimension, approximating a derivative. {'/'.join(BOUNDARY_KEYS)} markers determine how to handle boundaries for subsequent specs (default: {BOUNDARY_KEYS[0]}).",
    nargs="+",
)
def parse_partial(args: list[str]) -> Partial:
    return Partial(parse_diffs_1d(args, DIFF_FORMAT))
