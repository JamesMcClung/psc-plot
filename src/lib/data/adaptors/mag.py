import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--mag",
    help="take the (complex) absolute value",
)
class Magnitude(BareAdaptor):
    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def get_name_fragments(self) -> list[str]:
        return ["mag"]

    def get_modified_display_latex(self, display_latex: str, metadata) -> str:
        return f"|{display_latex}|"
