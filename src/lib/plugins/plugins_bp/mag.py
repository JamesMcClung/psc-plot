import xarray as xr

from ..plugin_base import PluginBp
from ..registry import register_const_plugin


class Magnitude(PluginBp):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def get_name_fragment(self) -> str:
        return f"mag"


register_const_plugin(
    "--mag",
    help="take the (complex) absolute value",
    const=Magnitude(),
)
