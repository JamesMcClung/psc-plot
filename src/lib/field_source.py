from abc import ABC, abstractmethod

import xarray as xr

from .adaptors.pipeline import Pipeline


class FieldSource(ABC):
    @abstractmethod
    def get_data(self, steps: list[int]) -> xr.DataArray: ...

    @abstractmethod
    def get_file_prefix(self) -> str:
        """The prefix of the data files that ultimately source the fields, e.g. 'pfd'"""

    @abstractmethod
    def get_var_name(self) -> str:
        """The plain-text name of the original, dependent variable"""

    @abstractmethod
    def get_modified_var_name(self) -> str:
        """The latex-formatted name (including applied formulae) of the dependent variable"""

    @abstractmethod
    def get_name_fragments(self) -> list[str]:
        """An ordered list of name fragments representing how this field is loaded and transformed"""


class FieldSourceWithPipeline(FieldSource):
    def __init__(self, source: FieldSource, pipeline: Pipeline[xr.DataArray]):
        self.source = source
        self.pipeline = pipeline

    def get_data(self, steps: list[int]) -> xr.DataArray:
        da = self.source.get_data(steps)
        da = self.pipeline.apply(da)
        return da

    def get_file_prefix(self) -> str:
        return self.source.get_file_prefix()

    def get_var_name(self) -> str:
        return self.source.get_var_name()

    def get_modified_var_name(self) -> str:
        return self.pipeline.get_modified_var_name(self.source.get_modified_var_name())

    def get_name_fragments(self) -> list[str]:
        return self.source.get_name_fragments() + self.pipeline.get_name_fragments()
