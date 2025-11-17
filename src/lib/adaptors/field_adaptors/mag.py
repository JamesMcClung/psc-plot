import xarray as xr

from ..adaptor_base import Adaptor
from ..registry import register_const_adaptor


class Magnitude(Adaptor[xr.DataArray]):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def get_name_fragment(self) -> str:
        return f"mag"

    def get_modified_var_name(self, title_stem: str) -> str:
        return f"|{title_stem}|"


register_const_adaptor(
    "--mag",
    help="take the (complex) absolute value",
    const=Magnitude(),
)
