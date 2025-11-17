from abc import ABC, abstractmethod

import xarray as xr


class FieldSource(ABC):
    @abstractmethod
    def get(self, steps: list[int]) -> xr.DataArray: ...
