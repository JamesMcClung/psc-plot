import xarray as xr

from ..plugin_base import PluginBp
from ..registry import register_const_plugin


class Imaginary(PluginBp):
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
