import xarray as xr

from ..plugin_base import PluginBp


class IdxSlice(PluginBp):
    def __init__(self, dim_name: str, lower_inclusive: int, upper_exclusive: int):
        self.dim_name = dim_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.isel({self.dim_name: slice(self.lower_inclusive, self.upper_exclusive)})
