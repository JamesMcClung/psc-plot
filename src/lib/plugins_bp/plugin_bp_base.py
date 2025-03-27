import abc

import xarray as xr


class PluginBp(abc.ABC):
    @abc.abstractmethod
    def apply(self, da: xr.DataArray) -> xr.DataArray: ...
