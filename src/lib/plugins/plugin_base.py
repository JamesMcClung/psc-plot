import abc

import pandas as pd
import xarray as xr

__all__ = ["PluginBp", "PluginH5"]


class Plugin[Data](abc.ABC):
    @abc.abstractmethod
    def apply(self, da: Data) -> Data: ...

    def get_name_fragment(self) -> str:
        return ""


class PluginBp(Plugin[xr.DataArray]):
    def get_modified_dep_var_name(self, dep_var_name: str) -> str:
        return dep_var_name


class PluginH5(Plugin[pd.DataFrame]): ...
