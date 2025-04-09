import abc

import pandas as pd
import xarray as xr

__all__ = ["PluginBp", "PluginH5"]


class Plugin[Data](abc.ABC):
    @abc.abstractmethod
    def apply(self, da: Data) -> Data: ...


type PluginBp = Plugin[xr.DataArray]
type PluginH5 = Plugin[pd.DataFrame]
