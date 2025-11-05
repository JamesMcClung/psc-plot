import abc

import pandas as pd
import xarray as xr

__all__ = ["FieldAdaptor", "ParticleAdaptor"]


class Adaptor[Data](abc.ABC):
    @abc.abstractmethod
    def apply(self, da: Data) -> Data: ...

    def get_name_fragment(self) -> str:
        return ""


class FieldAdaptor(Adaptor[xr.DataArray]):
    def get_modified_dep_var_name(self, dep_var_name: str) -> str:
        return dep_var_name


class ParticleAdaptor(Adaptor[pd.DataFrame]): ...
