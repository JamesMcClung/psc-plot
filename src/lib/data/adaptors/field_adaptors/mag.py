import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.adaptors.registry import const_adaptor


@const_adaptor(
    "--mag",
    help="take the (complex) absolute value",
)
class Magnitude(BareAdaptor):
    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def get_name_fragments(self) -> list[str]:
        return ["mag"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        return f"|{var_latex}|"
