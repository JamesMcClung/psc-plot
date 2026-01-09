import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--real",
    help="take the real part",
)
class Real(BareAdaptor):
    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def get_name_fragments(self) -> list[str]:
        return ["real"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        return f"\\text{{Re}}[{var_latex}]"
