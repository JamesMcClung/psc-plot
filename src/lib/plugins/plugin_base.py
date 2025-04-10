import abc
import typing

import pandas as pd
import xarray as xr

__all__ = ["PluginBp", "PluginH5"]


class Plugin[Data](abc.ABC):
    @abc.abstractmethod
    def apply(self, da: Data) -> Data: ...

    @classmethod
    @abc.abstractmethod
    def parse(cls, arg: str) -> typing.Self: ...


class PluginBp(Plugin[xr.DataArray]): ...


class PluginH5(Plugin[pd.DataFrame]): ...
