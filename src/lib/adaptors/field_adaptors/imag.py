import xarray as xr

from ..adaptor_base import Adaptor
from ..registry import register_const_adaptor


class Imaginary(Adaptor[xr.DataArray]):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.imag

    def get_name_fragment(self) -> str:
        return f"imag"

    def get_modified_var_name(self, title_stem: str) -> str:
        return f"\\text{{Im}}[{title_stem}]"


register_const_adaptor(
    "--imag",
    help="take the imaginary part",
    const=Imaginary(),
)
