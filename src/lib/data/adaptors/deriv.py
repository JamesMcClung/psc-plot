import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.adaptors.diff import BOUNDARY_KEYS, DIR_TO_SHIFT, _Diff1d, format_diffs_1d, parse_diffs_1d
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing.args_registry import arg_parser


class Deriv(BareAdaptor):
    def __init__(self, diffs_1d: list[_Diff1d]):
        self.diffs_1d = diffs_1d

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        dims = ",".join(diff_1d.dim_key for diff_1d in self.diffs_1d)
        return Latex(f"\\partial_{{{dims}}}{metadata.active_var_info.display}")

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for diff_1d in self.diffs_1d:
            coords = da.coords[diff_1d.dim_key]
            if len(coords) < 2:
                raise ValueError(f"--deriv needs at least 2 points along '{diff_1d.dim_key}'; got {len(coords)}")
            spacing = float(coords[1] - coords[0])
            da = diff_1d.apply_field_bare(da) / spacing
        return da

    def get_name_fragments(self) -> list[str]:
        return [f"deriv_{format_diffs_1d(self.diffs_1d)}"]


DERIV_FORMAT = f"[{' | '.join(BOUNDARY_KEYS)}] dim_key[,dim_key...]={set(DIR_TO_SHIFT)} [...]"


@arg_parser(
    dest="adaptors",
    flags="--deriv",
    metavar=DERIV_FORMAT,
    help=f"Like --diff, but divide each difference by the (uniform) grid spacing along its dimension, approximating a derivative. {'/'.join(BOUNDARY_KEYS)} markers determine how to handle boundaries for subsequent specs (default: {BOUNDARY_KEYS[0]}).",
    nargs="+",
)
def parse_deriv(args: list[str]) -> Deriv:
    return Deriv(parse_diffs_1d(args, DERIV_FORMAT))
