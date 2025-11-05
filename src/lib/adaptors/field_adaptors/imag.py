import xarray as xr

from ..adaptor_base import FieldAdaptor
from ..registry import register_const_plugin


class Imaginary(FieldAdaptor):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.imag

    def get_name_fragment(self) -> str:
        return f"imag"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"\\text{{Im}}[{title_stem}]"


register_const_plugin(
    "--imag",
    help="take the imaginary part",
    const=Imaginary(),
)
