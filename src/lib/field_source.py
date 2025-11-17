from abc import ABC, abstractmethod

import xarray as xr

from .adaptors.pipeline import FieldPipeline


class FieldSource(ABC):
    @abstractmethod
    def get_data(self, steps: list[int]) -> xr.DataArray: ...


class FieldSourceWithPipeline(FieldSource):
    def __init__(self, source: FieldSource, pipeline: FieldPipeline):
        self.source = source
        self.pipeline = pipeline

    def get_data(self, steps: list[int]) -> xr.DataArray:
        da = self.source.get_data(steps)
        da = self.pipeline.apply(da)
        return da
