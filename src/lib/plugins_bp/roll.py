import xarray as xr

from .plugin_bp_base import PluginBp


class Roll(PluginBp):
    def __init__(self, dim_name: str, roll_window: int):
        self.dim_name = dim_name
        self.window_size = roll_window

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.rolling({self.dim_name: self.window_size}).mean()
