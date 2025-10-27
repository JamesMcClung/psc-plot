import xarray as xr

from ..plugin_base import PluginBp
from ..registry import register_const_plugin


class Real(PluginBp):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def get_name_fragment(self) -> str:
        return f"real"

    def get_modified_title_stem(self, title_stem: str) -> str:
        return f"Re[{title_stem}]"


register_const_plugin(
    "--real",
    help="take the real part",
    const=Real(),
)
