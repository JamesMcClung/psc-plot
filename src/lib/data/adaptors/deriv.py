import numpy as np
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.adaptors.diff import BOUNDARY_KEYS, DIR_TO_SHIFT, _Diff1d, format_diffs_1d, parse_diffs_1d
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing.args_registry import arg_parser


def _spacing(diff_1d: _Diff1d, coord: xr.DataArray) -> xr.DataArray:
    """The coordinate difference matching `diff_1d`, per cell, so nonuniform grids work. Covers every cell; division aligns it to whichever cells the boundary kept."""
    c = coord.values
    if len(c) < 2:
        raise ValueError(f"--partial needs at least 2 points along '{diff_1d.dim_key}'; got {len(c)}")
    spacing = diff_1d.dir * (np.roll(c, -diff_1d.dir) - c)
    # the wrap-around cell spans the domain boundary, where the true spacing is unknown; assume the mean (exact for uniform grids)
    boundary_idx = 0 if diff_1d.dir == -1 else -1
    spacing[boundary_idx] = (c[-1] - c[0]) / (len(c) - 1)
    return xr.DataArray(spacing, coords={diff_1d.dim_key: c}, dims=diff_1d.dim_key)


class Deriv(BareAdaptor):
    def __init__(self, diffs_1d: list[_Diff1d]):
        self.diffs_1d = diffs_1d

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        dims = ",".join(diff_1d.dim_key for diff_1d in self.diffs_1d)
        return Latex(f"\\partial_{{{dims}}}{metadata.active_var_info.display}")

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for diff_1d in self.diffs_1d:
            da = diff_1d.apply_field_bare(da) / _spacing(diff_1d, da.coords[diff_1d.dim_key])
        return da

    def get_name_fragments(self) -> list[str]:
        return [f"partial_{format_diffs_1d(self.diffs_1d)}"]


DERIV_FORMAT = f"[{' | '.join(BOUNDARY_KEYS)}] dim_key[,dim_key...]={set(DIR_TO_SHIFT)} [...]"


@arg_parser(
    dest="adaptors",
    flags="--partial",
    metavar=DERIV_FORMAT,
    help=f"Like --diff, but divide each difference by the corresponding grid spacing along its dimension, approximating a derivative. {'/'.join(BOUNDARY_KEYS)} markers determine how to handle boundaries for subsequent specs (default: {BOUNDARY_KEYS[0]}).",
    nargs="+",
)
def parse_deriv(args: list[str]) -> Deriv:
    return Deriv(parse_diffs_1d(args, DERIV_FORMAT))
